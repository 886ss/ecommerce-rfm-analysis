"""Data preprocessing: load, validate, and clean transaction data."""
from __future__ import annotations

import logging

import pandas as pd

try:
    from .config import DATA_DIR, DATA_FILE
    from .schema import ColumnMapping, apply_mapping, validate_columns
except ImportError:
    from config import DATA_DIR, DATA_FILE  # type: ignore[import-not-found, no-redef]
    from schema import (  # type: ignore[import-not-found, no-redef]
        ColumnMapping,
        apply_mapping,
        validate_columns,
    )

logger = logging.getLogger(__name__)


def load_and_clean(
    data_path: str,
    *,
    mapping: ColumnMapping | None = None,
) -> pd.DataFrame:
    """Load raw transaction data, validate columns, clean, and normalise.

    Args:
        data_path: Path to an Excel / CSV file.
        mapping: Optional column-name mapping.  When provided, the file's
            columns are validated and renamed to internal standard names
            (CustomerID, InvoiceNo, InvoiceDate, Quantity, UnitPrice).
            When *None*, the file is assumed to already use UCI-standard
            column names.

    Cleaning steps:
        1. Validate required columns (if *mapping* provided).
        2. Rename user columns → internal standard names.
        3. Drop rows with missing CustomerID.
        4. Remove cancelled orders (configurable via *mapping*).
        5. Remove rows with non-positive Quantity or UnitPrice.
        6. Create ``Revenue = Quantity × UnitPrice``.
        7. Ensure InvoiceDate is datetime64.

    Returns:
        Cleaned DataFrame with internal standard column names.
    """
    # ── Load ──
    df = pd.read_excel(data_path, dtype={"CustomerID": "Int64"})
    logger.info("Raw: %s rows", f"{len(df):,}")

    # ── Validate & rename (user columns → internal standard names) ──
    if mapping is not None:
        validate_columns(df, mapping)
        df = apply_mapping(df, mapping)
        cancel_mode = mapping.cancel_mode
        cancel_value = mapping.cancel_value
    else:
        cancel_mode = "prefix"
        cancel_value = "C"

    # ── Clean ──
    df = df.dropna(subset=["CustomerID"])

    if cancel_mode == "prefix":
        df = df[~df["InvoiceNo"].astype(str).str.startswith(cancel_value, na=False)]
    # Future: elif cancel_mode == "column": ...

    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

    # ── Report ──
    logger.info("After cleaning: %s rows | %s customers | %s invoices",
                f"{len(df):,}", f"{df['CustomerID'].nunique():,}",
                f"{df['InvoiceNo'].nunique():,}")
    logger.info("Date range: %s → %s",
                df["InvoiceDate"].min().strftime("%Y-%m-%d"),
                df["InvoiceDate"].max().strftime("%Y-%m-%d"))
    logger.info("Total revenue: %s", f"£{df['Revenue'].sum():,.0f}")

    return df


if __name__ == "__main__":
    try:
        from .config import setup_logging
    except ImportError:
        from config import setup_logging  # type: ignore[no-redef]
    setup_logging()
    df = load_and_clean(str(DATA_DIR / DATA_FILE))
    print(df.head())
