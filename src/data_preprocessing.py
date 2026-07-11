"""Data preprocessing: load and clean UCI Online Retail dataset."""
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def load_and_clean(data_path: str) -> pd.DataFrame:
    """Load raw UCI Online Retail data and return cleaned DataFrame.

    Cleaning steps:
        1. Drop rows with missing CustomerID.
        2. Remove cancelled orders (InvoiceNo starting with 'C').
        3. Remove rows with non-positive Quantity or UnitPrice.
        4. Create Revenue = Quantity × UnitPrice column.
        5. Ensure InvoiceDate is datetime.
    """
    df = pd.read_excel(data_path, dtype={"CustomerID": "Int64"})

    logger.info("Raw: %s rows", f"{len(df):,}")

    df = df.dropna(subset=["CustomerID"])
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C", na=False)]
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]

    df["Revenue"] = df["Quantity"] * df["UnitPrice"]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

    logger.info("After cleaning: %s rows | %s customers | %s invoices",
                f"{len(df):,}", f"{df['CustomerID'].nunique():,}",
                f"{df['InvoiceNo'].nunique():,}")
    logger.info("Date range: %s → %s",
                df["InvoiceDate"].min().strftime("%Y-%m-%d"),
                df["InvoiceDate"].max().strftime("%Y-%m-%d"))
    logger.info("Total revenue: %s", f"£{df['Revenue'].sum():,.0f}")

    return df


if __name__ == "__main__":
    from config import DATA_DIR, DATA_FILE, setup_logging
    setup_logging()
    df = load_and_clean(str(DATA_DIR / DATA_FILE))
    print(df.head())
