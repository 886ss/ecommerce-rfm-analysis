import pandas as pd
import numpy as np
from pathlib import Path


def load_and_clean(data_path: str) -> pd.DataFrame:
    """Load raw UCI Online Retail data and return cleaned DataFrame."""
    df = pd.read_excel(data_path, dtype={"CustomerID": "Int64"})

    # Drop rows missing CustomerID (cannot attribute to a customer)
    df = df.dropna(subset=["CustomerID"])

    # Remove cancelled orders (InvoiceNo starts with 'C')
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C", na=False)]

    # Remove rows with non-positive Quantity or UnitPrice
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]

    # Create Revenue column
    df["Revenue"] = df["Quantity"] * df["UnitPrice"]

    # Ensure InvoiceDate is datetime
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])

    print(f"[Preprocessing] Raw: 541,909 rows")
    print(f"[Preprocessing] After cleaning: {len(df):,} rows")
    print(f"[Preprocessing] Unique customers: {df['CustomerID'].nunique():,}")
    print(f"[Preprocessing] Unique invoices: {df['InvoiceNo'].nunique():,}")
    print(f"[Preprocessing] Date range: {df['InvoiceDate'].min()} -> {df['InvoiceDate'].max()}")
    print(f"[Preprocessing] Total revenue: {df['Revenue'].sum():,.0f}")

    return df


if __name__ == "__main__":
    data_path = str(Path(__file__).parent.parent / "data" / "Online Retail.xlsx")
    df = load_and_clean(data_path)
    print(df.head())
