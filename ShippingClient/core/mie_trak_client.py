"""Utility functions to query Mie Trak directly from the client."""

from typing import Any, List
import pymssql
import logging

logger = logging.getLogger(__name__)


def get_mie_trak_address(job_number: str) -> str:
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
        conn = pymssql.connect(
            server="GUNDMAIN",
            user="mie",
            password="mie",
            database="GunderlinLive",
        )
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
