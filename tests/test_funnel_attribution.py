"""Tests for funnel_attribution — stage counting and drop-off logic."""
import pandas as pd
import pytest

from funnel_attribution import analyze_dropoff, build_funnel


@pytest.fixture
def sample_df():
    """Transactions with a clear purchase-count hierarchy."""
    records = []
    # 10 customers: 6 with 1 order, 2 with 3 orders, 1 with 6 orders, 1 with 10 orders
    for cid in range(1, 7):   # 6 customers × 1 order
        records.append({"CustomerID": cid, "InvoiceNo": f"INV_{cid}_1", "Revenue": 10})
    for cid in range(7, 9):    # 2 customers × 3 orders
        for o in range(1, 4):
            records.append({"CustomerID": cid, "InvoiceNo": f"INV_{cid}_{o}", "Revenue": 20})
    for o in range(1, 7):      # 1 customer × 6 orders (high spender)
        records.append({"CustomerID": 9, "InvoiceNo": f"INV_9_{o}", "Revenue": 100})
    for o in range(1, 11):     # 1 customer × 10 orders (top spender)
        records.append({"CustomerID": 10, "InvoiceNo": f"INV_10_{o}", "Revenue": 50})
    return pd.DataFrame(records)


class TestBuildFunnel:
    def test_total_customers(self, sample_df):
        funnel = build_funnel(sample_df)
        assert funnel.iloc[0]["Customers"] == 10

    def test_repeat_buyers(self, sample_df):
        funnel = build_funnel(sample_df)
        # 4 out of 10 customers have 2+ orders
        assert funnel.iloc[1]["Customers"] == 4

    def test_regular_buyers(self, sample_df):
        funnel = build_funnel(sample_df)
        # 2 out of 10 customers have 5+ orders
        assert funnel.iloc[2]["Customers"] == 2

    def test_all_stages_present(self, sample_df):
        funnel = build_funnel(sample_df)
        expected_stages = [
            "Total Customers", "Repeat Buyers", "Regular Buyers",
            "High-Value Buyers", "VIP Buyers",
        ]
        assert funnel["Stage"].tolist() == expected_stages

    def test_stage_conversion_in_range(self, sample_df):
        funnel = build_funnel(sample_df)
        assert (funnel["Stage_Conversion"] >= 0).all()
        assert (funnel["Stage_Conversion"] <= 100).all()


class TestAnalyzeDropoff:
    def test_returns_dict_with_dropoff_keys(self, sample_df):
        funnel = build_funnel(sample_df)
        insights = analyze_dropoff(funnel)
        assert "Repeat Buyers" in insights
        info = insights["Repeat Buyers"]
        assert "dropoff" in info
        assert "conversion" in info
        assert "lost_customers" in info

    def test_dropoff_plus_conversion_equals_100(self, sample_df):
        funnel = build_funnel(sample_df)
        insights = analyze_dropoff(funnel)
        for info in insights.values():
            assert abs(info["dropoff"] + info["conversion"] - 100) < 0.1
