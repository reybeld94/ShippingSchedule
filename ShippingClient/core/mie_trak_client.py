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


SILLS_SHORTAGE_QUERY = """
WITH ItemDemand AS (
    SELECT
        i.PartNumber,
        i.Description,
        wa.TotalQuantityRequired AS QtyNeeded,
        ISNULL(CAST(so.SalesOrderNumber AS VARCHAR(50)), '') + ' - '
            + CAST(wo.WorkOrderNumber AS VARCHAR(50))
            + ' - ' + ISNULL(wo.CustomDescription, '') AS WorkOrder,
        ISNULL(ii.QuantityOnHand, 0) AS QtyOnHand,
        i.ItemPK,
        i.LeadTime,
        wo.UserDefinedDate1,
        CAST(ISNULL(wo.UserDefinedDate1, DATEADD(DAY, 730, GETDATE())) AS DATE) AS WantedDate,
        SUBSTRING(i.PartNumber, 1, CHARINDEX('-', i.PartNumber + '-') - 1) AS Die,
        SUBSTRING(i.PartNumber,
            CHARINDEX('-', i.PartNumber + '-') + 1,
            CHARINDEX('-', i.PartNumber + '-', CHARINDEX('-', i.PartNumber + '-') + 1)
              - CHARINDEX('-', i.PartNumber + '-') - 1) AS Material,
        TRY_CAST(PARSENAME(REPLACE(i.PartNumber, '-', '.'), 2) AS INT) AS Length
    FROM dbo.WorkOrderAssembly AS wa
    INNER JOIN dbo.Item AS i ON wa.ItemFK = i.ItemPK
    INNER JOIN dbo.WorkOrder AS wo ON wo.WorkOrderPK = wa.WorkOrderFK
    LEFT JOIN dbo.ItemInventory AS ii ON i.ItemInventoryFK = ii.ItemInventoryPK
    LEFT JOIN dbo.SalesOrderLineLot AS soll ON soll.WorkOrderNumber = wo.WorkOrderNumber
    LEFT JOIN dbo.SalesOrderLine AS sol ON sol.SalesOrderLinePK = soll.SalesOrderLineFK
    LEFT JOIN dbo.SalesOrder AS so ON so.SalesOrderPK = sol.SalesOrderFK
    WHERE i.ItemClassFK = 1
      AND wa.WorkOrderAssemblyBOMStatusFK <> 5
      AND wo.WorkOrderStatusFK = 2
      AND TRY_CAST(PARSENAME(REPLACE(i.PartNumber, '-', '.'), 2) AS INT) IS NOT NULL
      AND i.InactiveDate IS NULL
    GROUP BY i.PartNumber, i.Description, wa.TotalQuantityRequired, wo.WorkOrderNumber,
             wo.CustomDescription, ii.QuantityOnHand, i.ItemPK, i.LeadTime,
             wo.UserDefinedDate1, so.SalesOrderNumber
),
QtyOnPO_Promised AS (
    SELECT pol.ItemFK,
           DATEADD(DAY, ISNULL(i.LeadTime, 0), po.CreateDate) AS ETA,
           pol.Quantity - pol.QuantityReceived AS QtyIncoming
    FROM dbo.PurchaseOrderLine AS pol
    INNER JOIN dbo.PurchaseOrder AS po ON po.PurchaseOrderPK = pol.PurchaseOrderFK
    INNER JOIN dbo.Item AS i ON pol.ItemFK = i.ItemPK
    WHERE po.PurchaseOrderStatusFK = 2 AND (pol.Quantity - pol.QuantityReceived > 0)
),
DemandSequence AS (
    SELECT d.*,
           ROW_NUMBER() OVER (PARTITION BY d.PartNumber ORDER BY d.WantedDate, d.WorkOrder) AS SequenceNumber
    FROM ItemDemand d
),
RunningInventory AS (
    SELECT ds.*,
           ISNULL((SELECT SUM(q.QtyIncoming) FROM QtyOnPO_Promised q
                   WHERE q.ItemFK = ds.ItemPK AND q.ETA <= ds.WantedDate), 0) AS POsReceivedByDate,
           ds.QtyOnHand
             + ISNULL((SELECT SUM(q.QtyIncoming) FROM QtyOnPO_Promised q
                       WHERE q.ItemFK = ds.ItemPK AND q.ETA <= ds.WantedDate), 0)
             - ISNULL((SELECT SUM(ds2.QtyNeeded) FROM DemandSequence ds2
                       WHERE ds2.PartNumber = ds.PartNumber AND ds2.SequenceNumber < ds.SequenceNumber), 0)
             AS AvailableForThisOrder
    FROM DemandSequence ds
),
ShortageCalculation AS (
    SELECT r.*,
           CASE WHEN r.AvailableForThisOrder < r.QtyNeeded
                THEN r.QtyNeeded - CASE WHEN r.AvailableForThisOrder > 0 THEN r.AvailableForThisOrder ELSE 0 END
                ELSE 0 END AS ActualShortage,
           CASE WHEN (r.QtyNeeded - CASE WHEN r.AvailableForThisOrder > 0 THEN r.AvailableForThisOrder ELSE 0 END) > 0
                THEN 'Short' ELSE 'OK' END AS InventoryStatus
    FROM RunningInventory r
),
Final AS (
    SELECT s.PartNumber, s.Description,
           CAST(s.QtyOnHand AS INT) AS QtyOnHand,
           CAST(s.QtyNeeded AS INT) AS QtyNeeded,
           s.WorkOrder, s.WantedDate,
           (SELECT SUM(d2.QtyNeeded) FROM ItemDemand d2
            WHERE d2.PartNumber = s.PartNumber AND d2.WantedDate = s.WantedDate) AS ProjectedDemand,
           s.POsReceivedByDate,
           (SELECT MIN(q.ETA) FROM QtyOnPO_Promised q
            WHERE q.ItemFK = s.ItemPK AND q.ETA <= s.WantedDate) AS NextPOETA,
           CASE WHEN s.ActualShortage > 0 THEN
                CASE WHEN DATEADD(DAY, -ISNULL(s.LeadTime,0), s.WantedDate) < CAST(GETDATE() AS DATE)
                     THEN 'LATE - Order ASAP'
                     ELSE 'Order ' + CAST(CAST(s.ActualShortage AS INT) AS VARCHAR(10))
                          + ' by ' + CONVERT(VARCHAR(10), DATEADD(DAY, -ISNULL(s.LeadTime,0), s.WantedDate), 101)
                END
                ELSE '' END AS Proposal,
           CAST(s.ActualShortage AS INT) AS Short,
           s.InventoryStatus AS Status,
           s.ItemPK, s.Length AS NeededLength, s.Die, s.Material, s.LeadTime,
           DATEADD(DAY, -ISNULL(s.LeadTime,0), s.WantedDate) AS OrderByDate
    FROM ShortageCalculation s
)
SELECT DISTINCT
    F.PartNumber, F.Description, F.QtyOnHand, F.QtyNeeded, F.WantedDate,
    CASE WHEN W.ShopDate IS NOT NULL THEN CONVERT(VARCHAR(10), W.ShopDate, 101)
         WHEN W.WeekEnding IS NOT NULL THEN CONVERT(VARCHAR(10), W.WeekEnding, 101)
         ELSE 'Backlog' END AS Schedule,
    CONVERT(VARCHAR(10), W.WeekEnding, 101) AS WeekEnding,
    ISNULL(F.WorkOrder, '') AS WorkOrder, F.ProjectedDemand,
    F.POsReceivedByDate, F.NextPOETA, F.Proposal, F.Short, F.Status,
    F.ItemPK, F.NeededLength, F.Die, F.Material, F.LeadTime, F.OrderByDate
FROM Final AS F
CROSS APPLY (
    SELECT TRY_CONVERT(INT, LTRIM(RTRIM(SUBSTRING(F.WorkOrder,
        CHARINDEX(' - ', F.WorkOrder) + 3,
        CHARINDEX(' - ', F.WorkOrder, CHARINDEX(' - ', F.WorkOrder) + 3)
          - (CHARINDEX(' - ', F.WorkOrder) + 3))))) AS WO
) AS X
OUTER APPLY (
    SELECT MAX(TRY_CONVERT(date, e.ShopDate)) AS ShopDate,
           MAX(TRY_CONVERT(date, e.WeekEnding)) AS WeekEnding
    FROM dbo.MieTrak_Excel_Schedule AS e
    WHERE TRY_CONVERT(INT, e.WorkOrderNumber) = X.WO
) AS W
"""


def get_sills_shortage_view(
    *,
    server: str = DEFAULT_MIE_TRAK_SERVER,
    database: str = DEFAULT_MIE_TRAK_DATABASE,
) -> list[dict]:
    """Run the unscheduled-sills shortage report. One row per WO/PartNumber/WantedDate."""
    conn = None
    try:
        conn = _connect_to_mie_trak(server=server, database=database)
        cursor = conn.cursor(as_dict=True)
        cursor.execute(SILLS_SHORTAGE_QUERY)
        rows = cursor.fetchall() or []
        return [dict(row) for row in rows if row]
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_sills_open_purchase_orders(
    *,
    server: str = DEFAULT_MIE_TRAK_SERVER,
    database: str = DEFAULT_MIE_TRAK_DATABASE,
) -> list[dict]:
    """Open PO lines for sill items (ItemClassFK = 1), ETA = CreateDate + LeadTime."""
    query = """
        SELECT
            po.PurchaseOrderNumber,
            po.CreateDate,
            DATEADD(DAY, ISNULL(i.LeadTime, 0), po.CreateDate) AS ETA,
            i.ItemPK,
            i.PartNumber,
            i.Description,
            i.LeadTime,
            pol.Quantity,
            pol.QuantityReceived,
            (pol.Quantity - pol.QuantityReceived) AS QtyIncoming,
            party.Name AS VendorName,
            SUBSTRING(i.PartNumber, 1, CHARINDEX('-', i.PartNumber + '-') - 1) AS Die,
            SUBSTRING(i.PartNumber,
                CHARINDEX('-', i.PartNumber + '-') + 1,
                CHARINDEX('-', i.PartNumber + '-', CHARINDEX('-', i.PartNumber + '-') + 1)
                  - CHARINDEX('-', i.PartNumber + '-') - 1) AS Material,
            TRY_CAST(PARSENAME(REPLACE(i.PartNumber, '-', '.'), 2) AS INT) AS Length
        FROM dbo.PurchaseOrderLine pol
        INNER JOIN dbo.PurchaseOrder po ON po.PurchaseOrderPK = pol.PurchaseOrderFK
        INNER JOIN dbo.Item i ON i.ItemPK = pol.ItemFK
        LEFT JOIN dbo.PartySupplier ps ON ps.PartySupplierPK = po.SupplierFK
        LEFT JOIN dbo.Party party ON party.PartyPK = ps.PartyFK
        WHERE po.PurchaseOrderStatusFK = 2
          AND (pol.Quantity - pol.QuantityReceived) > 0
          AND i.ItemClassFK = 1
          AND i.InactiveDate IS NULL
        ORDER BY ETA, i.PartNumber
    """
    conn = None
    try:
        conn = _connect_to_mie_trak(server=server, database=database)
        cursor = conn.cursor(as_dict=True)
        cursor.execute(query)
        rows = cursor.fetchall() or []
        return [dict(row) for row in rows if row]
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def get_sills_inventory_by_part(
    *,
    server: str = DEFAULT_MIE_TRAK_SERVER,
    database: str = DEFAULT_MIE_TRAK_DATABASE,
) -> list[dict]:
    """On-hand inventory for every active sill item (ItemClassFK = 1)."""
    query = """
        SELECT
            i.ItemPK,
            i.PartNumber,
            i.Description,
            i.LeadTime,
            ISNULL(ii.QuantityOnHand, 0) AS QuantityOnHand,
            SUBSTRING(i.PartNumber, 1, CHARINDEX('-', i.PartNumber + '-') - 1) AS Die,
            SUBSTRING(i.PartNumber,
                CHARINDEX('-', i.PartNumber + '-') + 1,
                CHARINDEX('-', i.PartNumber + '-', CHARINDEX('-', i.PartNumber + '-') + 1)
                  - CHARINDEX('-', i.PartNumber + '-') - 1) AS Material,
            TRY_CAST(PARSENAME(REPLACE(i.PartNumber, '-', '.'), 2) AS INT) AS Length
        FROM dbo.Item i
        LEFT JOIN dbo.ItemInventory ii ON ii.ItemInventoryPK = i.ItemInventoryFK
        WHERE i.ItemClassFK = 1
          AND i.InactiveDate IS NULL
          AND TRY_CAST(PARSENAME(REPLACE(i.PartNumber, '-', '.'), 2) AS INT) IS NOT NULL
        ORDER BY i.PartNumber
    """
    conn = None
    try:
        conn = _connect_to_mie_trak(server=server, database=database)
        cursor = conn.cursor(as_dict=True)
        cursor.execute(query)
        rows = cursor.fetchall() or []
        return [dict(row) for row in rows if row]
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

