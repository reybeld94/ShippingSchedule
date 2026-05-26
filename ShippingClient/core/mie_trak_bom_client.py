"""SolidWorks BOM ↔ Mie Trak sandbox importer.

CRITICAL SAFETY CONTRACT
========================
This module is HARDCODED to use the ``GunderlinSandbox`` database. It will
NEVER connect to ``GunderlinLive`` regardless of how it is invoked. Every
connection helper asserts the database name before opening the socket.

If you ever need to point this at production, do not edit ``SANDBOX_DATABASE``
in place — fork the module or add an explicit opt-in flag with a code review.

Insert procedure
----------------
For each (Item, Qty) row the importer:

1. Resolves the top-level ``WorkOrderRelease`` of the target Work Order
   (``ParentRouterFK IS NULL``) and reuses its ``WorkOrderReleasePK`` and
   ``RouterFK``.
2. Looks up an existing BOM line matching the same ``ItemFK`` in that release
   with ``WorkCenterFK IS NULL`` and ``ItemRouterFK IS NULL``.
   - If found → UPDATE QuantityRequired += @AddQuantity (the documented
     safe path from the conversation PDF).
   - If not found → INSERT new BOM row with the patterns observed in
     Work Order 4879 (the lab WO):
        WorkCenterFK         = NULL
        ItemRouterFK         = NULL
        Released             = 1
        BOMStatusFK          = 1
        PartsRequired        = 1
        QuantityToFabricate  = 0
3. After all rows are processed, runs the Mie Trak housekeeping procedures
   so denormalized data is refreshed exactly like the GUI would:
        EXEC usp_AssignWorkOrderAssembly @WorkOrderFK = ...
        EXEC usp_CalculateWorkOrder      @WorkOrderPK = ...

Everything happens inside a single transaction. Any failure ROLLBACKs.
"""

from __future__ import annotations

import csv
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pymssql

from .mie_trak_client import (
    DEFAULT_MIE_TRAK_PASSWORD,
    DEFAULT_MIE_TRAK_SERVER,
    DEFAULT_MIE_TRAK_USER,
)

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
# Hard safety boundary — this module ONLY talks to GunderlinSandbox.
# ════════════════════════════════════════════════════════════════════════════
SANDBOX_DATABASE: str = "GunderlinSandbox"
PRODUCTION_DATABASE_BLOCKED: str = "GunderlinLive"


def _assert_sandbox(database: str) -> str:
    """Raise unless the caller resolved the sandbox database.

    Returns the database string back for inline chaining. This is the single
    chokepoint that prevents accidentally pointing at production.
    """
    if database != SANDBOX_DATABASE:
        raise RuntimeError(
            f"BOM importer is sandbox-only. Refusing to connect to "
            f"database={database!r}. Must be exactly {SANDBOX_DATABASE!r}."
        )
    return database


def _connect_sandbox(server: str = DEFAULT_MIE_TRAK_SERVER):
    """Open a pymssql connection guaranteed to land on the sandbox DB."""
    _assert_sandbox(SANDBOX_DATABASE)
    conn = pymssql.connect(
        server=server,
        user=DEFAULT_MIE_TRAK_USER,
        password=DEFAULT_MIE_TRAK_PASSWORD,
        database=SANDBOX_DATABASE,
    )
    # Double-check by asking the server what DB we actually got. If somehow
    # the connection resolved to anything other than the sandbox we abort.
    cursor = conn.cursor()
    cursor.execute("SELECT DB_NAME(), @@SERVERNAME, SUSER_SNAME()")
    db, srv, login = cursor.fetchone()
    logger.info(
        "BOM sandbox connection established: server=%s db=%s login=%s",
        srv, db, login,
    )
    if str(db) != SANDBOX_DATABASE:
        try:
            conn.close()
        except Exception:
            pass
        raise RuntimeError(
            f"Sandbox guard failed: connection landed on {db!r} instead of "
            f"{SANDBOX_DATABASE!r}."
        )
    return conn


def get_sandbox_connection_info(server: str = DEFAULT_MIE_TRAK_SERVER) -> Dict[str, str]:
    """Return what server/db/login the sandbox connection actually uses.

    This is the diagnostic the UI shows next to the sandbox banner so the
    operator can visually confirm we are NOT on production.
    """
    conn = None
    try:
        conn = _connect_sandbox(server=server)
        cursor = conn.cursor()
        cursor.execute("SELECT DB_NAME(), @@SERVERNAME, SUSER_SNAME(), GETDATE()")
        db, srv, login, now = cursor.fetchone()
        return {
            "server": str(srv or ""),
            "database": str(db or ""),
            "login": str(login or ""),
            "server_time": str(now or ""),
        }
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ════════════════════════════════════════════════════════════════════════════
# SolidWorks → BOM extraction
# ════════════════════════════════════════════════════════════════════════════
# Port of the legacy BOM/extract_bom.py + BOM/parse.py logic. Keeps the
# same expected macro location so the existing macro install still works.

SW_DOC_DRAWING = 3
SW_OPEN_SILENT = 1
SW_OPEN_LOADMODEL = 32
SW_OPEN_OPTS = SW_OPEN_SILENT | SW_OPEN_LOADMODEL

DEFAULT_MACRO_PATH = r"C:\ProgramData\BOMReader\SolidWorks\ExportBomToCsv.swp"
DEFAULT_MACRO_MODULE = "ExportBomToCsv1"
DEFAULT_MACRO_PROC = "main"


def _norm_header(s: str) -> str:
    return (s or "").strip().lower()


def _find_csv_col(headers: List[str], keys: Iterable[str]) -> Optional[int]:
    norm = [_norm_header(h) for h in headers]
    for key in keys:
        key_lower = key.lower()
        for idx, name in enumerate(norm):
            if key_lower in name:
                return idx
    return None


def _parse_qty(value: str) -> Optional[float]:
    s = (value or "").strip()
    if not s:
        return None
    s = s.replace(",", "")
    m = re.search(r"[-+]?\d*\.?\d+", s)
    if not m:
        return None
    f = float(m.group(0))
    return int(f) if abs(f - int(f)) < 1e-9 else f


def parse_bom_csv(csv_path: str) -> Tuple[List[str], List[dict]]:
    """Parse a SolidWorks-exported BOM CSV into rows.

    Returns (headers, rows). Each row dict has keys:
      item_no, part_number, finish, description, qty
    """
    with open(csv_path, "r", encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.reader(f))

    if not rows:
        raise RuntimeError(f"CSV BOM vacío: {csv_path}")

    headers = rows[0]
    col_item = _find_csv_col(headers, ["item no", "item"])
    col_part = _find_csv_col(headers, ["part number", "part"])
    col_finish = _find_csv_col(headers, ["finish"])
    col_desc = _find_csv_col(headers, ["description", "desc"])
    col_qty = _find_csv_col(headers, ["qty", "quantity"])

    if col_part is None or col_qty is None:
        raise RuntimeError(
            f"No se pudo detectar columnas PART/QTY en el CSV. Headers: {headers}"
        )

    def get(r, idx):
        return (r[idx].strip() if idx is not None and idx < len(r) else "")

    bom: List[dict] = []
    for r in rows[1:]:
        if not any((x or "").strip() for x in r):
            continue
        part = get(r, col_part)
        if not part:
            continue
        bom.append({
            "item_no": get(r, col_item),
            "part_number": part,
            "finish": get(r, col_finish),
            "description": get(r, col_desc),
            "qty": _parse_qty(get(r, col_qty)),
        })

    return headers, bom


def expected_temp_csv(drw_path: str) -> str:
    base = os.path.splitext(os.path.basename(drw_path))[0]
    temp = os.environ.get("TEMP") or os.environ.get("TMP") or "."
    return os.path.join(temp, f"{base}_BOM.csv")


def extract_bom_from_slddrw(
    drw_path: str,
    *,
    visible: bool = True,
    wait_seconds: float = 30.0,
    macro_path: str = DEFAULT_MACRO_PATH,
    macro_module: str = DEFAULT_MACRO_MODULE,
    macro_proc: str = DEFAULT_MACRO_PROC,
) -> Tuple[List[str], List[dict], str]:
    """Run SolidWorks (via COM) → macro → parse the CSV it produces.

    Returns (headers, bom_rows, csv_path).

    Raises RuntimeError if SolidWorks, the macro, or the CSV is unavailable.
    win32com / pythoncom are imported lazily so this module still loads on
    machines without SolidWorks installed (e.g. for unit tests or the CSV
    path).
    """
    if not os.path.exists(drw_path):
        raise FileNotFoundError(f"Drawing no existe: {drw_path}")
    if not os.path.exists(macro_path):
        raise FileNotFoundError(
            f"Macro de SolidWorks no encontrado: {macro_path}. "
            f"Instala el SWP o usa la opción 'Cargar CSV' como fallback."
        )

    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 no está instalado. No puedo invocar SolidWorks por COM. "
            "Instala pywin32 o usa la opción 'Cargar CSV'."
        ) from exc

    def _byref_i4(v: int = 0):
        return win32com.client.VARIANT(0x4003, v)  # VT_BYREF | VT_I4

    sw = win32com.client.DispatchEx("SldWorks.Application")
    sw.Visible = bool(visible)

    err = _byref_i4(0)
    warn = _byref_i4(0)

    doc = sw.OpenDoc6(drw_path, SW_DOC_DRAWING, SW_OPEN_OPTS, "", err, warn)
    if doc is None:
        raise RuntimeError(
            f"SolidWorks no pudo abrir el .SLDDRW. err={err.value} warn={warn.value}"
        )

    try:
        a_err = _byref_i4(0)
        sw.ActivateDoc2(os.path.basename(drw_path), False, a_err)
    except Exception:
        pass

    out_csv = expected_temp_csv(drw_path)
    if os.path.exists(out_csv):
        try:
            os.remove(out_csv)
        except Exception:
            pass

    run_err = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    rc = sw.RunMacro2(macro_path, macro_module, macro_proc, 0, run_err)
    if not rc or run_err.value != 0:
        raise RuntimeError(f"Macro de SolidWorks no ejecutó. rc={rc} err={run_err.value}")

    deadline = time.time() + float(wait_seconds)
    while time.time() < deadline:
        if os.path.exists(out_csv) and os.path.getsize(out_csv) > 0:
            break
        time.sleep(0.25)

    if not os.path.exists(out_csv):
        raise RuntimeError(f"SolidWorks no generó el CSV BOM esperado: {out_csv}")

    headers, bom = parse_bom_csv(out_csv)
    return headers, bom, out_csv


# ════════════════════════════════════════════════════════════════════════════
# Matching SW BOM ↔ Mie Trak Item table
# ════════════════════════════════════════════════════════════════════════════


@dataclass
class ItemMatch:
    """Result of looking up one SW part number against sandbox Item."""
    part_number: str
    found: bool
    item_pk: Optional[int] = None
    matched_part_number: Optional[str] = None
    description: Optional[str] = None
    item_type_fk: Optional[int] = None


def match_items_in_sandbox(
    part_numbers: Iterable[str],
    *,
    server: str = DEFAULT_MIE_TRAK_SERVER,
) -> Dict[str, ItemMatch]:
    """Look up every part number against ``Item.PartNumber`` (sandbox DB).

    The comparison is case-sensitive exact match per Mie Trak convention.
    Returns a dict keyed by the *input* part number so callers can preserve
    SW row order.
    """
    cleaned = [str(p or "").strip() for p in part_numbers]
    cleaned = [p for p in cleaned if p]
    if not cleaned:
        return {}

    unique = sorted(set(cleaned))
    out: Dict[str, ItemMatch] = {p: ItemMatch(part_number=p, found=False) for p in cleaned}

    conn = None
    try:
        conn = _connect_sandbox(server=server)
        cursor = conn.cursor(as_dict=True)
        # Use a temp-table-friendly IN clause. pymssql doesn't support array
        # params, so build placeholders inline.
        placeholders = ",".join(["%s"] * len(unique))
        query = (
            f"SELECT ItemPK, PartNumber, Description, ItemTypeFK "
            f"FROM Item WHERE PartNumber IN ({placeholders})"
        )
        cursor.execute(query, tuple(unique))
        rows = cursor.fetchall() or []

        by_pn = {str(r["PartNumber"]): r for r in rows if r.get("PartNumber")}
        for pn in cleaned:
            row = by_pn.get(pn)
            if row:
                out[pn] = ItemMatch(
                    part_number=pn,
                    found=True,
                    item_pk=int(row["ItemPK"]) if row.get("ItemPK") is not None else None,
                    matched_part_number=str(row.get("PartNumber") or ""),
                    description=str(row.get("Description") or ""),
                    item_type_fk=int(row["ItemTypeFK"]) if row.get("ItemTypeFK") is not None else None,
                )
        return out
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ════════════════════════════════════════════════════════════════════════════
# Sales Order / Work Order picker (sandbox-scoped versions)
# ════════════════════════════════════════════════════════════════════════════


def search_sandbox_sales_orders(
    search_term: str,
    *,
    server: str = DEFAULT_MIE_TRAK_SERVER,
    limit: int = 50,
) -> List[dict]:
    cleaned = str(search_term or "").strip()
    if not cleaned:
        return []
    safe_limit = max(1, min(int(limit), 200))
    like_value = f"%{cleaned}%"
    query = f"""
        SELECT DISTINCT TOP {safe_limit}
            so.SalesOrderPK,
            so.SalesOrderNumber
        FROM SalesOrder so
        WHERE CAST(so.SalesOrderPK AS VARCHAR(50)) LIKE %s
           OR so.SalesOrderNumber LIKE %s
        ORDER BY so.SalesOrderPK DESC
    """
    conn = None
    try:
        conn = _connect_sandbox(server=server)
        cursor = conn.cursor(as_dict=True)
        cursor.execute(query, (like_value, like_value))
        return [
            {
                "sales_order_pk": str(row.get("SalesOrderPK") or "").strip(),
                "sales_order_number": str(row.get("SalesOrderNumber") or "").strip(),
            }
            for row in cursor.fetchall() or []
        ]
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def get_sandbox_work_orders_by_sales_order(
    sales_order_pk: str,
    *,
    server: str = DEFAULT_MIE_TRAK_SERVER,
) -> List[dict]:
    cleaned = str(sales_order_pk or "").strip()
    if "." in cleaned:
        cleaned = cleaned.split(".", 1)[0]
    if not cleaned:
        return []

    query = """
        SELECT DISTINCT
            wo.WorkOrderPK,
            wo.WorkOrderNumber,
            wo.PartNumber,
            wo.CustomDescription,
            wo.DueDate
        FROM SalesOrder so
        INNER JOIN SalesOrderLine sol
            ON sol.SalesOrderFK = so.SalesOrderPK
        INNER JOIN SalesOrderLineLot soll
            ON soll.SalesOrderLineFK = sol.SalesOrderLinePK
        INNER JOIN WorkOrderJob woj
            ON woj.SalesOrderLineLotFK = soll.SalesOrderLineLotPK
        INNER JOIN WorkOrder wo
            ON wo.WorkOrderPK = woj.WorkOrderFK
        WHERE so.SalesOrderPK = %s
        ORDER BY wo.WorkOrderNumber
    """
    conn = None
    try:
        conn = _connect_sandbox(server=server)
        cursor = conn.cursor(as_dict=True)
        cursor.execute(query, (cleaned,))
        return [
            {
                "work_order_pk": str(row.get("WorkOrderPK") or "").strip(),
                "work_order_number": str(row.get("WorkOrderNumber") or "").strip(),
                "part_number": str(row.get("PartNumber") or "").strip(),
                "description": str(row.get("CustomDescription") or "").strip(),
                "due_date": str(row.get("DueDate") or "").strip(),
            }
            for row in cursor.fetchall() or []
        ]
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ════════════════════════════════════════════════════════════════════════════
# Safe BOM import → WorkOrderAssembly
# ════════════════════════════════════════════════════════════════════════════


@dataclass
class BomImportItem:
    """One row queued for import.

    ``item_pk`` must already be resolved (call ``match_items_in_sandbox``
    first) — the importer refuses to insert lines with unknown items.
    """
    part_number: str
    item_pk: int
    quantity: float
    description: str = ""


@dataclass
class BomImportLineResult:
    part_number: str
    item_pk: int
    action: str  # "INSERTED" | "UPDATED" | "SKIPPED" | "ERROR"
    work_order_assembly_pk: Optional[int] = None
    quantity_required: Optional[float] = None
    detail: str = ""


@dataclass
class BomImportResult:
    work_order_pk: int
    work_order_release_fk: Optional[int]
    router_fk: Optional[int]
    database: str = SANDBOX_DATABASE
    committed: bool = False
    rolled_back: bool = False
    error: Optional[str] = None
    lines: List[BomImportLineResult] = field(default_factory=list)
    sequence_number: Optional[int] = None


def _find_top_level_release(cursor, work_order_pk: int) -> Tuple[Optional[int], Optional[int]]:
    """Return (WorkOrderReleasePK, RouterFK) for the WO top-level release."""
    cursor.execute(
        """
        SELECT TOP 1 WorkOrderReleasePK, RouterFK
        FROM WorkOrderRelease
        WHERE WorkOrderFK = %s
          AND ParentRouterFK IS NULL
        ORDER BY WorkOrderReleasePK ASC
        """,
        (work_order_pk,),
    )
    row = cursor.fetchone()
    if not row:
        return None, None
    return int(row[0]), (int(row[1]) if row[1] is not None else None)


def _next_sequence_number(cursor, work_order_pk: int, release_fk: int) -> int:
    """Return MAX(SequenceNumber)+1 or 1 if none exists."""
    cursor.execute(
        """
        SELECT ISNULL(MAX(SequenceNumber), 0)
        FROM WorkOrderAssembly
        WHERE WorkOrderFK = %s AND WorkOrderReleaseFK = %s
        """,
        (work_order_pk, release_fk),
    )
    row = cursor.fetchone()
    base = int(row[0] or 0)
    return base + 1


def import_bom_to_work_order(
    work_order_pk: int,
    items: List[BomImportItem],
    *,
    server: str = DEFAULT_MIE_TRAK_SERVER,
    dry_run: bool = False,
) -> BomImportResult:
    """Insert (or top up) BOM lines on a sandbox Work Order.

    All lines are processed inside a single transaction. If ``dry_run`` is
    True the transaction is ALWAYS rolled back so callers can preview the
    result. Otherwise the transaction is committed only when every line
    finishes without error.
    """
    _assert_sandbox(SANDBOX_DATABASE)
    work_order_pk = int(work_order_pk)
    result = BomImportResult(
        work_order_pk=work_order_pk,
        work_order_release_fk=None,
        router_fk=None,
    )

    if not items:
        result.error = "No hay items para importar."
        return result

    # Defensive validation before opening a connection
    for it in items:
        if not it.item_pk:
            result.error = f"Item '{it.part_number}' no tiene ItemPK resuelto."
            return result
        if it.quantity is None or float(it.quantity) <= 0:
            result.error = f"Item '{it.part_number}' tiene quantity inválida: {it.quantity}"
            return result

    conn = None
    try:
        conn = _connect_sandbox(server=server)
        # pymssql opens transactions implicitly; we manage commit/rollback.
        cursor = conn.cursor()

        # Confirm runtime DB one more time before any write.
        cursor.execute("SELECT DB_NAME()")
        live_db = str(cursor.fetchone()[0])
        if live_db != SANDBOX_DATABASE:
            raise RuntimeError(
                f"Sandbox guard failed inside transaction: DB_NAME()={live_db!r}"
            )

        release_fk, router_fk = _find_top_level_release(cursor, work_order_pk)
        if release_fk is None:
            raise RuntimeError(
                f"No se encontró WorkOrderRelease top-level para WorkOrderPK={work_order_pk}."
            )
        result.work_order_release_fk = release_fk
        result.router_fk = router_fk

        next_seq = _next_sequence_number(cursor, work_order_pk, release_fk)
        result.sequence_number = next_seq

        # Process each item: UPDATE if already a BOM line, else INSERT.
        for it in items:
            qty = float(it.quantity)
            # Duplicate check using the exact pattern from the PDF.
            cursor.execute(
                """
                SELECT TOP 1 WorkOrderAssemblyPK, ISNULL(QuantityRequired, 0)
                FROM WorkOrderAssembly
                WHERE WorkOrderFK = %s
                  AND WorkOrderReleaseFK = %s
                  AND ItemFK = %s
                  AND WorkCenterFK IS NULL
                  AND ItemRouterFK IS NULL
                """,
                (work_order_pk, release_fk, int(it.item_pk)),
            )
            existing = cursor.fetchone()

            if existing is not None:
                existing_pk = int(existing[0])
                current_qty = float(existing[1] or 0)
                new_qty = current_qty + qty
                cursor.execute(
                    """
                    UPDATE WorkOrderAssembly
                    SET QuantityRequired = %s
                    WHERE WorkOrderAssemblyPK = %s
                    """,
                    (new_qty, existing_pk),
                )
                result.lines.append(BomImportLineResult(
                    part_number=it.part_number,
                    item_pk=int(it.item_pk),
                    action="UPDATED",
                    work_order_assembly_pk=existing_pk,
                    quantity_required=new_qty,
                    detail=f"Was {current_qty} → {new_qty}",
                ))
            else:
                cursor.execute(
                    """
                    INSERT INTO WorkOrderAssembly (
                        WorkOrderFK,
                        WorkOrderReleaseFK,
                        RouterFK,
                        ParentRouterFK,
                        SequenceNumber,
                        WorkCenterFK,
                        ItemFK,
                        ItemRouterFK,
                        Released,
                        WorkOrderAssemblyBOMStatusFK,
                        QuantityRequired,
                        PartsRequired,
                        QuantityToFabricate
                    )
                    OUTPUT INSERTED.WorkOrderAssemblyPK
                    VALUES (%s, %s, %s, NULL, %s, NULL, %s, NULL, 1, 1, %s, 1, 0)
                    """,
                    (
                        work_order_pk,
                        release_fk,
                        router_fk,
                        next_seq,
                        int(it.item_pk),
                        qty,
                    ),
                )
                new_pk_row = cursor.fetchone()
                new_pk = int(new_pk_row[0]) if new_pk_row else None
                result.lines.append(BomImportLineResult(
                    part_number=it.part_number,
                    item_pk=int(it.item_pk),
                    action="INSERTED",
                    work_order_assembly_pk=new_pk,
                    quantity_required=qty,
                    detail=f"New row at SequenceNumber={next_seq}",
                ))

        # Mie Trak housekeeping — exactly what the GUI button does.
        cursor.execute("EXEC usp_AssignWorkOrderAssembly @WorkOrderFK = %s", (work_order_pk,))
        cursor.execute("EXEC usp_CalculateWorkOrder @WorkOrderPK = %s", (work_order_pk,))

        if dry_run:
            conn.rollback()
            result.rolled_back = True
        else:
            conn.commit()
            result.committed = True
        return result

    except Exception as exc:
        if conn is not None:
            try:
                conn.rollback()
                result.rolled_back = True
            except Exception:
                pass
        result.error = str(exc)
        logger.exception("BOM import to sandbox failed: %s", exc)
        return result
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
