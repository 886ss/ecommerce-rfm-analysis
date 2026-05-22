"""
RFM Analysis: Recency, Frequency, Monetary user segmentation.
Uses quintile scoring (1-5) and maps to standard RFM segments.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from data_preprocessing import load_and_clean


def compute_rfm(df: pd.DataFrame, reference_date: pd.Timestamp) -> pd.DataFrame:
    """Compute RFM metrics per customer."""
    rfm = df.groupby("CustomerID").agg(
        Recency=("InvoiceDate", lambda x: (reference_date - x.max()).days),
        Frequency=("InvoiceNo", "nunique"),
        Monetary=("Revenue", "sum"),
    ).reset_index()

    rfm.columns = ["CustomerID", "Recency", "Frequency", "Monetary"]
    return rfm


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    """Assign quintile scores 1-5 to each RFM dimension.
    Recency: lower is better → reversed scoring.
    Frequency & Monetary: higher is better.
    """
    rfm["R_Score"] = pd.qcut(rfm["Recency"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F_Score"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M_Score"] = pd.qcut(rfm["Monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    rfm["RFM_Score"] = rfm["R_Score"] + rfm["F_Score"] + rfm["M_Score"]
    return rfm


def segment_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    """Map RFM scores to customer segments."""
    def _segment(row):
        r, f, m = row["R_Score"], row["F_Score"], row["M_Score"]
        total = r + f + m

        if total >= 13:
            return "Champions"
        elif total >= 11:
            return "Loyal Customers"
        elif total >= 9:
            if r >= 4:
                return "Potential Loyalists"
            elif f >= 4:
                return "At Risk"
            else:
                return "Needs Attention"
        elif total >= 7:
            if r >= 4:
                return "New Customers"
            elif f >= 3:
                return "About to Sleep"
            else:
                return "Hibernating"
        elif total >= 5:
            if r >= 3:
                return "Promising"
            else:
                return "Lost"
        else:
            return "Lost"

    rfm["Segment"] = rfm.apply(_segment, axis=1)
    return rfm


def summarize_segments(rfm: pd.DataFrame) -> pd.DataFrame:
    """Print and return segment summary statistics."""
    summary = rfm.groupby("Segment").agg(
        Customers=("CustomerID", "count"),
        Avg_Recency=("Recency", "mean"),
        Avg_Frequency=("Frequency", "mean"),
        Avg_Monetary=("Monetary", "mean"),
        Total_Revenue=("Monetary", "sum"),
        Pct_Revenue=("Monetary", lambda x: x.sum() / rfm["Monetary"].sum() * 100),
    ).sort_values("Total_Revenue", ascending=False)

    summary["Avg_Recency"] = summary["Avg_Recency"].round(1)
    summary["Avg_Frequency"] = summary["Avg_Frequency"].round(1)
    summary["Avg_Monetary"] = summary["Avg_Monetary"].round(0)
    summary["Total_Revenue"] = summary["Total_Revenue"].round(0)
    summary["Pct_Revenue"] = summary["Pct_Revenue"].round(1)

    return summary


def plot_rfm(rfm: pd.DataFrame, output_dir: str):
    """Generate RFM visualization charts."""
    # 1. Segment distribution pie chart
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    seg_counts = rfm["Segment"].value_counts()
    colors = ["#2ecc71", "#3498db", "#9b59b6", "#f39c12", "#e74c3c",
              "#1abc9c", "#e67e22", "#95a5a6", "#34495e", "#7f8c8d"]
    wedges, texts, autotexts = axes[0].pie(
        seg_counts.values, labels=seg_counts.index, autopct="%1.1f%%",
        colors=colors[:len(seg_counts)], startangle=140, textprops={"fontsize": 8}
    )
    axes[0].set_title("RFM Customer Segmentation", fontsize=13, fontweight="bold")

    # 2. Revenue contribution by segment (horizontal bar)
    seg_rev = rfm.groupby("Segment")["Monetary"].sum().sort_values()
    bars = axes[1].barh(seg_rev.index, seg_rev.values / 1e6, color="#3498db", edgecolor="white")
    axes[1].set_xlabel("Total Revenue (Million GBP)", fontsize=11)
    axes[1].set_title("Revenue by Segment", fontsize=13, fontweight="bold")
    for bar, val in zip(bars, seg_rev.values):
        axes[1].text(bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
                     f"{val/1e6:.2f}M", va="center", fontsize=8)

    plt.tight_layout()
    path = str(Path(output_dir) / "rfm_segments.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[RFM] Chart saved: {path}")


def run_rfm(data_path: str, output_dir: str):
    df = load_and_clean(data_path)

    # Reference date: day after last transaction
    ref_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)
    print(f"[RFM] Reference date: {ref_date.date()}")

    rfm = compute_rfm(df, ref_date)
    rfm = score_rfm(rfm)
    rfm = segment_rfm(rfm)

    summary = summarize_segments(rfm)
    print("\n[RFM] Segment Summary:")
    print(summary.to_string())

    plot_rfm(rfm, output_dir)

    # Save RFM table
    rfm_path = Path(output_dir) / "rfm_table.csv"
    rfm.to_csv(rfm_path, index=False)
    print(f"[RFM] Table saved: {rfm_path}")

    return rfm, summary


if __name__ == "__main__":
    DATA = str(Path(__file__).parent.parent / "data" / "Online Retail.xlsx")
    OUT = str(Path(__file__).parent.parent / "output")
    run_rfm(DATA, OUT)
