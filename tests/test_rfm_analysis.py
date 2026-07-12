"""Tests for rfm_analysis — scoring boundaries and segment mapping."""
import pandas as pd
import pytest

from rfm_analysis import compute_rfm, score_rfm, segment_rfm


@pytest.fixture
def sample_transactions():
    """Create a small set of transactions with varied purchase patterns."""
    return pd.DataFrame({
        "CustomerID": [1, 1, 1, 2, 2, 3, 3, 3, 3, 3, 4],
        "InvoiceNo": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"],
        "InvoiceDate": pd.to_datetime([
            "2023-01-01", "2023-02-01", "2023-03-01",  # cust 1: 3 orders
            "2023-01-15", "2023-01-16",                 # cust 2: 2 orders, close
            "2023-06-01", "2023-06-15", "2023-07-01",  # cust 3: 5 orders, recent
            "2023-07-15", "2023-08-01",
            "2023-01-01",                                # cust 4: 1 order, long ago
        ]),
        "Revenue": [100, 200, 150, 50, 60, 500, 500, 500, 500, 1000, 20],
    })


@pytest.fixture
def ref_date():
    return pd.Timestamp("2023-09-01")


class TestComputeRFM:
    def test_returns_expected_columns(self, sample_transactions, ref_date):
        rfm = compute_rfm(sample_transactions, ref_date)
        assert list(rfm.columns) == ["CustomerID", "Recency", "Frequency", "Monetary"]

    def test_frequency_counts_unique_invoices(self, sample_transactions, ref_date):
        rfm = compute_rfm(sample_transactions, ref_date)
        cust3 = rfm[rfm["CustomerID"] == 3].iloc[0]
        assert cust3["Frequency"] == 5  # invoices F-J

    def test_monetary_sums_revenue(self, sample_transactions, ref_date):
        rfm = compute_rfm(sample_transactions, ref_date)
        cust1 = rfm[rfm["CustomerID"] == 1].iloc[0]
        assert cust1["Monetary"] == 450  # 100+200+150


class TestScoreRFM:
    def test_scores_are_in_range_1_to_5(self, sample_transactions, ref_date):
        rfm = compute_rfm(sample_transactions, ref_date)
        scored = score_rfm(rfm)
        for col in ["R_Score", "F_Score", "M_Score"]:
            assert scored[col].between(1, 5).all()

    def test_rfm_score_is_sum(self, sample_transactions, ref_date):
        rfm = compute_rfm(sample_transactions, ref_date)
        scored = score_rfm(rfm)
        expected = scored["R_Score"] + scored["F_Score"] + scored["M_Score"]
        assert (scored["RFM_Score"] == expected).all()

    def test_handles_duplicate_values(self, sample_transactions, ref_date):
        """When many customers have the same Frequency, qcut should not crash."""
        rfm = compute_rfm(sample_transactions, ref_date)
        # Artificially make all Frequencies identical
        rfm["Frequency"] = 1
        rfm["Monetary"] = 100
        scored = score_rfm(rfm)
        assert "R_Score" in scored.columns
        assert "F_Score" in scored.columns


class TestSegmentRFM:
    def test_segment_column_exists(self, sample_transactions, ref_date):
        rfm = compute_rfm(sample_transactions, ref_date)
        scored = score_rfm(rfm)
        seg = segment_rfm(scored)
        assert "Segment" in seg.columns

    def test_all_segments_are_valid(self, sample_transactions, ref_date):
        valid = {
            "Champions", "Loyal Customers", "Potential Loyalists",
            "At Risk", "Needs Attention", "New Customers",
            "About to Sleep", "Hibernating", "Promising", "Lost",
        }
        rfm = compute_rfm(sample_transactions, ref_date)
        scored = score_rfm(rfm)
        seg = segment_rfm(scored)
        assert set(seg["Segment"].unique()).issubset(valid)

    def test_vectorized_matches_original_logic(self, sample_transactions, ref_date):
        """The np.select vectorised path must produce identical segments
        to the old apply(axis=1) approach — spot-checked against known cases."""
        rfm = compute_rfm(sample_transactions, ref_date)
        scored = score_rfm(rfm)
        seg = segment_rfm(scored)

        # Cust 3: highest Frequency (5), most recent → highest R score, high F, high M
        cust3 = seg[seg["CustomerID"] == 3].iloc[0]
        assert cust3["Segment"] in {"Champions", "Loyal Customers"}

        # Cust 4: 1 purchase, long ago → low scores → Lost
        cust4 = seg[seg["CustomerID"] == 4].iloc[0]
        assert cust4["Segment"] == "Lost"
