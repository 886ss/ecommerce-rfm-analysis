"""Tests for clv_estimation — CLV calculation and segment summary."""
import pandas as pd
import pytest

from clv_estimation import estimate_clv, summarize_clv_by_segment


@pytest.fixture
def sample_transactions():
    """Two customers with known purchase histories."""
    return pd.DataFrame({
        "CustomerID": [1, 1, 1, 2, 2],
        "InvoiceNo": ["A", "B", "C", "D", "E"],
        "InvoiceDate": pd.to_datetime([
            "2023-01-01", "2023-02-01", "2023-03-01",
            "2023-06-01", "2023-06-15",
        ]),
        "Quantity": [2, 3, 1, 1, 2],
        "Revenue": [100, 200, 150, 500, 600],
    })


@pytest.fixture
def sample_rfm(sample_transactions):
    """Minimal RFM table matching the two customers."""
    return pd.DataFrame({
        "CustomerID": [1, 2],
        "Recency": [183, 78],
        "Frequency": [3, 2],
        "Monetary": [450, 1100],
        "R_Score": [3, 4],
        "F_Score": [4, 3],
        "M_Score": [3, 5],
        "RFM_Score": [10, 12],
        "Segment": ["Needs Attention", "Loyal Customers"],
    })


class TestEstimateCLV:
    def test_returns_expected_columns(self, sample_transactions, sample_rfm):
        clv = estimate_clv(sample_transactions, sample_rfm)
        for col in ["AOV", "Lifespan_Days", "Historical_CLV", "Predictive_CLV_12m"]:
            assert col in clv.columns

    def test_historical_clv_equals_total_revenue(self, sample_transactions, sample_rfm):
        clv = estimate_clv(sample_transactions, sample_rfm)
        cust1 = clv[clv["CustomerID"] == 1].iloc[0]
        assert cust1["Historical_CLV"] == 450  # 100+200+150

    def test_aov_calculation(self, sample_transactions, sample_rfm):
        clv = estimate_clv(sample_transactions, sample_rfm)
        cust1 = clv[clv["CustomerID"] == 1].iloc[0]
        assert cust1["AOV"] == 150  # 450 / 3 orders

    def test_lifespan_is_at_least_minimum(self, sample_transactions, sample_rfm):
        clv = estimate_clv(sample_transactions, sample_rfm)
        # Customer 2: first and last purchase within 14 days
        cust2 = clv[clv["CustomerID"] == 2].iloc[0]
        assert cust2["Lifespan_Days"] >= 30  # clipped to minimum

    def test_predictive_clv_is_positive(self, sample_transactions, sample_rfm):
        clv = estimate_clv(sample_transactions, sample_rfm)
        assert (clv["Predictive_CLV_12m"] > 0).all()

    def test_merges_rfm_segments(self, sample_transactions, sample_rfm):
        clv = estimate_clv(sample_transactions, sample_rfm)
        assert "Segment" in clv.columns
        assert len(clv) == 2


class TestSummarizeCLVBySegment:
    def test_returns_one_row_per_segment(self, sample_transactions, sample_rfm):
        clv = estimate_clv(sample_transactions, sample_rfm)
        summary = summarize_clv_by_segment(clv)
        assert len(summary) == 2  # Needs Attention + Loyal Customers

    def test_pct_revenue_sums_to_100(self, sample_transactions, sample_rfm):
        clv = estimate_clv(sample_transactions, sample_rfm)
        summary = summarize_clv_by_segment(clv)
        assert abs(summary["Pct_of_Total_Revenue"].sum() - 100) < 0.1
