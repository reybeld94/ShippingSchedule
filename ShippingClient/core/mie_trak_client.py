"""Utility functions to query Mie Trak directly from the client."""

from typing import Any, List
import pymssql
import logging

logger = logging.getLogger(__name__)

DEFAULT_MIE_TRAK_SERVER = "GUNDMAIN"
DEFAULT_MIE_TRAK_DATABASE = "GunderlinLive"
DEFAULT_MIE_TRAK_USER = "mie"
DEFAULT_MIE_TRAK_PASSWORD = "mie"


def _connect_to_mie_trak(server: str, database: str):
    return pymssql.connect(
        server=server,
        user=DEFAULT_MIE_TRAK_USER,
        password=DEFAULT_MIE_TRAK_PASSWORD,
        database=database,
    )


def get_mie_trak_databases(server: str = DEFAULT_MIE_TRAK_SERVER) -> list[str]:
    """Return online database names available in the target SQL Server."""
    conn = None
    try:
        conn = pymssql.connect(
            server=server,
            user=DEFAULT_MIE_TRAK_USER,
            password=DEFAULT_MIE_TRAK_PASSWORD,
            database="master",
        )
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name
            FROM sys.databases
            WHERE state_desc = 'ONLINE'
            ORDER BY name
            """
        )
        return [str(row[0]) for row in cursor.fetchall() if row and row[0]]
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_mie_trak_address(
    job_number: str,
    *,
    server: str = DEFAULT_MIE_TRAK_SERVER,
    database: str = DEFAULT_MIE_TRAK_DATABASE,
) -> str:
    """Return the shipping address for a given job number.

    This function connects directly to the Mie Trak database, queries the
    address information and closes the connection before returning.
    """
    raw_job_number = job_number
    cleaned_job_number = str(job_number).strip()

    # If the job number contains a suffix (e.g. "12345.1"), remove it before
    # querying Mie Trak. The DB only stores the base number.
    if "." in cleaned_job_number:
        cleaned_job_number = cleaned_job_number.split(".", 1)[0]

    variants: List[Any] = [cleaned_job_number]
    if cleaned_job_number.isdigit():
        variants.extend([
            cleaned_job_number.zfill(len(cleaned_job_number) + 1),
            int(cleaned_job_number),
        ])
    variants = list(dict.fromkeys(variants))

    conn = None
    try:
        conn = _connect_to_mie_trak(server=server, database=database)
        cursor = conn.cursor(as_dict=True)

        query = (
            """
            SELECT ShippingAddress1, ShippingAddress2,
                   ShippingAddressCity, ShippingAddressStateDescription,
                   ShippingAddressZipCode
            FROM SalesOrder
            WHERE SalesOrderPK = %s
            """
        )

        row = None
        for variant in variants:
            cursor.execute(query, (variant,))
            row = cursor.fetchone()
            if row:
                break

        if not row:
            raise ValueError(
                f"Job number {raw_job_number} not found. Variants tried: {variants}"
            )

        address_parts = [row.get("ShippingAddress1"), row.get("ShippingAddress2")]
        city_line = (
            f"{row.get('ShippingAddressCity')},{row.get('ShippingAddressStateDescription')} "
            f"{row.get('ShippingAddressZipCode')}"
        )
        address_parts.append(city_line)
        return "\n".join(part for part in address_parts if part)

    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def search_mie_trak_sales_orders(
    search_term: str,
    *,
    server: str = DEFAULT_MIE_TRAK_SERVER,
    database: str = DEFAULT_MIE_TRAK_DATABASE,
    limit: int = 25,
) -> list[dict[str, str]]:
    """Search Mie Trak sales orders with related PROD work orders."""
    cleaned_search = str(search_term or "").strip()
    if not cleaned_search:
        return []

    safe_limit = max(1, min(int(limit), 100))
    like_value = f"%{cleaned_search}%"
    query = f"""
        SELECT DISTINCT TOP {safe_limit}
            so.SalesOrderPK,
            so.SalesOrderNumber
        FROM SalesOrder so
        INNER JOIN SalesOrderLine sol
            ON sol.SalesOrderFK = so.SalesOrderPK
        INNER JOIN SalesOrderLineLot soll
            ON soll.SalesOrderLineFK = sol.SalesOrderLinePK
        INNER JOIN WorkOrderJob woj
            ON woj.SalesOrderLineLotFK = soll.SalesOrderLineLotPK
        INNER JOIN WorkOrder wo
            ON wo.WorkOrderPK = woj.WorkOrderFK
        WHERE wo.PartNumber LIKE '%PROD%'
          AND (
                CAST(so.SalesOrderPK AS VARCHAR(50)) LIKE %s
                OR so.SalesOrderNumber LIKE %s
              )
        ORDER BY so.SalesOrderPK DESC
    """

    conn = None
    try:
        conn = _connect_to_mie_trak(server=server, database=database)
        cursor = conn.cursor(as_dict=True)
        cursor.execute(query, (like_value, like_value))
        rows = cursor.fetchall() or []
        return [
            {
                "sales_order_pk": str(row.get("SalesOrderPK") or "").strip(),
                "sales_order_number": str(row.get("SalesOrderNumber") or "").strip(),
            }
            for row in rows
            if row
        ]
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_mie_trak_work_orders_by_sales_order(
    sales_order_pk: str,
    *,
    server: str = DEFAULT_MIE_TRAK_SERVER,
    database: str = DEFAULT_MIE_TRAK_DATABASE,
) -> list[dict[str, str]]:
    """Return work orders and descriptions for a given sales order."""
    cleaned_sales_order_pk = str(sales_order_pk or "").strip()
    if "." in cleaned_sales_order_pk:
        cleaned_sales_order_pk = cleaned_sales_order_pk.split(".", 1)[0]
    if not cleaned_sales_order_pk:
        return []

    query = """
        SELECT DISTINCT
            so.SalesOrderPK,
            so.SalesOrderNumber,
            wo.WorkOrderNumber,
            wo.CustomDescription
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
          AND wo.PartNumber LIKE '%PROD%'
        ORDER BY wo.WorkOrderNumber
    """
    conn = None
    try:
        conn = _connect_to_mie_trak(server=server, database=database)
        cursor = conn.cursor(as_dict=True)
        cursor.execute(query, (cleaned_sales_order_pk,))
        rows = cursor.fetchall() or []
        return [
            {
                "sales_order_pk": str(row.get("SalesOrderPK") or "").strip(),
                "sales_order_number": str(row.get("SalesOrderNumber") or "").strip(),
                "work_order_number": str(row.get("WorkOrderNumber") or "").strip(),
                "description": str(row.get("CustomDescription") or "").strip(),
            }
            for row in rows
            if row
        ]
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
