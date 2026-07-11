"""Tests for data_preprocessing — cleaning logic on small mock DataFrames."""
import pandas as pd
import pytest

from data_preprocessing import load_and_clean


@pytest.fixture
def sample_excel(tmp_path):
    """Create a minimal Excel file simulating UCI Online Retail columns."""
    df = pd.DataFrame({
        "InvoiceNo": ["536365", "536365", "C536366", "536367", "536368"],
        "StockCode": ["85123A", "71053", "84406B", "84029G", "84029E"],
        "Description": ["WHITE HANGER", "WHITE METAL", "CREAM CUPID", "KNITTED", "RED WOOLLY"],
        "Quantity": [6, 6, 3, -1, 0],
        "InvoiceDate": pd.to_datetime([
            "2010-12-01 08:26", "2010-12-01 08:26",
            "2010-12-01 08:30", "2010-12-01 09:00",
            "2010-12-01 09:30",
        ]),
        "UnitPrice": [2.55, 3.39, 2.75, 3.39, 4.25],
        "CustomerID": pd.array([17850, 17850, 17850, None, 17851], dtype="Int64"),
        "Country": ["UK", "UK", "UK", "UK", "UK"],
    })
    path = tmp_path / "test_sample.xlsx"
    df.to_excel(path, index=False)
    return str(path)


class TestLoadAndClean:
    def test_drops_missing_customer_id(self, sample_excel):
        df = load_and_clean(sample_excel)
        assert 17850 in df["CustomerID"].values
        # Row with CustomerID=None should be dropped
        assert df["CustomerID"].isna().sum() == 0

    def test_removes_cancelled_orders(self, sample_excel):
        df = load_and_clean(sample_excel)
        # InvoiceNo starting with 'C' should be removed
        assert not df["InvoiceNo"].astype(str).str.startswith("C").any()

    def test_removes_non_positive_quantity(self, sample_excel):
        df = load_and_clean(sample_excel)
        assert (df["Quantity"] > 0).all()

    def test_creates_revenue_column(self, sample_excel):
        df = load_and_clean(sample_excel)
        assert "Revenue" in df.columns
        assert (df["Revenue"] == df["Quantity"] * df["UnitPrice"]).all()

    def test_invoice_date_is_datetime(self, sample_excel):
        df = load_and_clean(sample_excel)
        assert pd.api.types.is_datetime64_any_dtype(df["InvoiceDate"])
