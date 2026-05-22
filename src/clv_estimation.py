"""
CLV Estimation: Customer Lifetime Value estimation using
historical revenue and a simple predictive model.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from data_preprocessing import load_and_clean
from rfm_analysis import compute_rfm, score_rfm, segment_rfm


def estimate_clv(cleaned_df: pd.DataFrame, rfm: pd.DataFrame) -> pd.DataFrame:
    """Estimate CLV for each customer using historical + predictive approach."""
    ref_date = cleaned_df["InvoiceDate"].max()

    cust = cleaned_df.groupby("CustomerID").agg(
        Total_Revenue=("Revenue", "sum"),
        Total_Orders=("InvoiceNo", "nunique"),
        Total_Items=("Quantity", "sum"),
        First_Purchase=("InvoiceDate", "min"),
        Last_Purchase=("InvoiceDate", "max"),
    ).reset_index()

    cust["AOV"] = cust["Total_Revenue"] / cust["Total_Orders"]
    cust["Lifespan_Days"] = (cust["Last_Purchase"] - cust["First_Purchase"]).dt.days
    cust["Lifespan_Days"] = cust["Lifespan_Days"].clip(lower=1)
    cust["Purchase_Freq"] = cust["Total_Orders"] / (cust["Lifespan_Days"] / 30)

    obs_months = max((ref_date - cust["First_Purchase"]).dt.days.mean() / 30, 1)

    cust["Historical_CLV"] = cust["Total_Revenue"]
    cust["Predictive_CLV_12m"] = cust["AOV"] * cust["Purchase_Freq"].clip(upper=10) * 12

    # Merge: include Recency, Frequency, Monetary from rfm
    merge_cols = ["CustomerID", "Recency", "Frequency", "Monetary",
                  "R_Score", "F_Score", "M_Score", "RFM_Score", "Segment"]
    clv = cust.merge(rfm[merge_cols], on="CustomerID", how="left")

    return clv


def summarize_clv_by_segment(clv: pd.DataFrame) -> pd.DataFrame:
    summary = clv.groupby("Segment").agg(
        Customers=("CustomerID", "count"),
        Avg_Historical_CLV=("Historical_CLV", "mean"),
        Median_Historical_CLV=("Historical_CLV", "median"),
        Avg_Predictive_CLV_12m=("Predictive_CLV_12m", "mean"),
        Total_Historical_Revenue=("Historical_CLV", "sum"),
        Pct_of_Total_Revenue=("Historical_CLV", lambda x: x.sum() / clv["Historical_CLV"].sum() * 100),
        Avg_AOV=("AOV", "mean"),
        Avg_Lifespan_Days=("Lifespan_Days", "mean"),
    ).sort_values("Avg_Historical_CLV", ascending=False)

    for col in ["Avg_Historical_CLV", "Median_Historical_CLV", "Avg_Predictive_CLV_12m",
                "Avg_AOV", "Total_Historical_Revenue"]:
        summary[col] = summary[col].round(0)
    summary["Avg_Lifespan_Days"] = summary["Avg_Lifespan_Days"].round(0)
    summary["Pct_of_Total_Revenue"] = summary["Pct_of_Total_Revenue"].round(1)

    return summary


def plot_clv(clv: pd.DataFrame, output_dir: str):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Boxplot by segment (top 5 by count)
    top_segs = clv["Segment"].value_counts().head(5).index.tolist()
    plot_data = clv[clv["Segment"].isin(top_segs)].copy()
    plot_data["Log_CLV"] = np.log1p(plot_data["Historical_CLV"])

    box_data = [plot_data[plot_data["Segment"] == s]["Log_CLV"].values for s in top_segs]
    bp = axes[0].boxplot(
        box_data, tick_labels=top_segs, patch_artist=True, showfliers=False,
        boxprops=dict(facecolor="#3498db", alpha=0.7),
        medianprops=dict(color="darkred", linewidth=2),
    )
    axes[0].set_title("Historical CLV Distribution by Segment (log scale)", fontsize=11, fontweight="bold")
    axes[0].set_ylabel("Log(1 + CLV)", fontsize=10)
    axes[0].tick_params(axis="x", rotation=20, labelsize=8)

    # Scatter: Recency vs Monetary, colored by segment
    seg_colors = {
        "Champions": "#2ecc71", "Loyal Customers": "#3498db",
        "Potential Loyalists": "#9b59b6", "At Risk": "#f39c12",
        "Needs Attention": "#e74c3c", "New Customers": "#1abc9c",
        "About to Sleep": "#e67e22", "Promising": "#2c3e50",
        "Hibernating": "#95a5a6", "Lost": "#bdc3c7",
    }
    for seg in top_segs:
        subset = clv[clv["Segment"] == seg]
        axes[1].scatter(subset["Recency"], np.log1p(subset["Historical_CLV"]),
                        c=seg_colors.get(seg, "gray"), label=seg, alpha=0.5, s=15)
    axes[1].set_xlabel("Recency (days)", fontsize=10)
    axes[1].set_ylabel("Log(1 + Historical CLV)", fontsize=10)
    axes[1].set_title("Recency vs CLV by Segment", fontsize=11, fontweight="bold")
    axes[1].legend(fontsize=7, loc="upper right", markerscale=2)

    plt.tight_layout()
    path = str(Path(output_dir) / "clv_analysis.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[CLV] Chart saved: {path}")


def run_clv(data_path: str, output_dir: str):
    df = load_and_clean(data_path)
    ref_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)
    rfm = compute_rfm(df, ref_date)
    rfm = score_rfm(rfm)
    rfm = segment_rfm(rfm)

    clv = estimate_clv(df, rfm)
    summary = summarize_clv_by_segment(clv)

    print("\n[CLV] Segment CLV Summary:")
    print(summary.to_string())

    print(f"\n[CLV] Overall Metrics:")
    print(f"  Avg Historical CLV: {clv['Historical_CLV'].mean():,.0f}")
    print(f"  Median Historical CLV: {clv['Historical_CLV'].median():,.0f}")
    print(f"  Total Revenue Captured: {clv['Historical_CLV'].sum():,.0f}")
    print(f"  Avg AOV: {clv['AOV'].mean():.2f}")
    print(f"  Avg Lifespan: {clv['Lifespan_Days'].mean():.0f} days")

    plot_clv(clv, output_dir)

    clv_path = Path(output_dir) / "clv_table.csv"
    clv.to_csv(clv_path, index=False)
    print(f"[CLV] Table saved: {clv_path}")

    return clv, summary


if __name__ == "__main__":
    DATA = str(Path(__file__).parent.parent / "data" / "Online Retail.xlsx")
    OUT = str(Path(__file__).parent.parent / "output")
    run_clv(DATA, OUT)
