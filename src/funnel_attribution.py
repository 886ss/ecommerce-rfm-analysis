"""
Funnel Attribution Analysis: maps the customer journey from first purchase
through repeat purchase to VIP status, identifying the largest drop-off points.
"""
import logging
from pathlib import Path

import pandas as pd

try:
    from .plotting import save_chart, plt
except ImportError:
    from plotting import save_chart, plt  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

FUNNEL_STAGE_NAMES = [
    "Total Customers",
    "Repeat Buyers",
    "Regular Buyers",
    "High-Value Buyers",
    "VIP Buyers",
]


def build_funnel(df: pd.DataFrame, rfm: pd.DataFrame | None = None) -> pd.DataFrame:
    """Build purchase-based conversion funnel from cleaned transactions.

    Accepts an optional pre-computed RFM table to avoid a redundant
    CustomerID groupby when called from the main pipeline.
    """
    if rfm is not None and "Frequency" in rfm.columns and "Monetary" in rfm.columns:
        purchase_counts = rfm.set_index("CustomerID")["Frequency"]
        total_spend = rfm.set_index("CustomerID")["Monetary"]
        total = len(rfm)
    else:
        cust = df.groupby("CustomerID").agg(
            Total_Spend=("Revenue", "sum"),
            Purchase_Count=("InvoiceNo", "nunique"),
        )
        purchase_counts = cust["Purchase_Count"]
        total_spend = cust["Total_Spend"]
        total = len(cust)

    thresholds = total_spend.quantile([0.80, 0.95])

    stage_counts = {
        "Total Customers":   total,
        "Repeat Buyers":     int((purchase_counts >= 2).sum()),
        "Regular Buyers":    int((purchase_counts >= 5).sum()),
        "High-Value Buyers": int((total_spend >= thresholds.iloc[0]).sum()),
        "VIP Buyers":        int((total_spend >= thresholds.iloc[1]).sum()),
    }

    rows = [
        {"Stage": name, "Customers": stage_counts[name],
         "Pct_of_Total": round(stage_counts[name] / total * 100, 1)}
        for name in FUNNEL_STAGE_NAMES
    ]
    funnel_df = pd.DataFrame(rows)

    # Stage-to-stage conversion rates
    conv_rates: list[float] = [100.0]
    for i in range(1, len(funnel_df)):
        prev = funnel_df.iloc[i - 1]["Customers"]
        curr = funnel_df.iloc[i]["Customers"]
        conv_rates.append(round(curr / prev * 100, 1) if prev > 0 else 0.0)
    funnel_df["Stage_Conversion"] = conv_rates

    return funnel_df


def analyze_dropoff(funnel_df: pd.DataFrame) -> dict[str, dict]:
    """Identify drop-off magnitude at each funnel transition."""
    insights: dict[str, dict] = {}
    for i in range(1, len(funnel_df)):
        stage_name = funnel_df.iloc[i]["Stage"]
        prev_cust = int(funnel_df.iloc[i - 1]["Customers"])
        curr_cust = int(funnel_df.iloc[i]["Customers"])
        insights[stage_name] = {
            "from": funnel_df.iloc[i - 1]["Stage"],
            "to": stage_name,
            "conversion": funnel_df.iloc[i]["Stage_Conversion"],
            "dropoff": round(100 - funnel_df.iloc[i]["Stage_Conversion"], 1),
            "lost_customers": prev_cust - curr_cust,
        }
    return insights


def plot_funnel(funnel_df: pd.DataFrame, output_dir: str) -> None:
    """Draw funnel chart + drop-off bar chart."""
    _, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    # ── Funnel (horizontal bars, reversed) ──
    stages = funnel_df["Stage"].iloc[::-1].tolist()
    counts = funnel_df["Customers"].iloc[::-1].tolist()
    colors = ["#9b59b6", "#e74c3c", "#f39c12", "#3498db", "#2ecc71"]

    axes[0].barh(stages, counts, color=colors, edgecolor="white", height=0.6)
    axes[0].set_xlabel("Number of Customers", fontsize=11)
    axes[0].set_title("Customer Funnel", fontsize=13, fontweight="bold")
    for i, (s, c) in enumerate(zip(stages, counts)):
        pct = funnel_df.iloc[::-1].iloc[i]["Pct_of_Total"]
        axes[0].text(c + max(counts) * 0.01, i,
                     f"{c:,} ({pct}%)", va="center", fontsize=9)

    # ── Drop-off rates ──
    drop_labels = []
    drop_vals = []
    for i in range(1, len(funnel_df)):
        label = (f"{funnel_df.iloc[i-1]['Stage']}\n"
                 f"→ {funnel_df.iloc[i]['Stage']}")
        drop_labels.append(label)
        drop_vals.append(100 - funnel_df.iloc[i]["Stage_Conversion"])

    bar_colors = [
        "#e74c3c" if v > 50 else "#f39c12" if v > 30 else "#3498db"
        for v in drop_vals
    ]
    axes[1].barh(drop_labels, drop_vals, color=bar_colors,
                 edgecolor="white", height=0.5)
    axes[1].set_xlabel("Drop-off Rate (%)", fontsize=11)
    axes[1].set_title("Funnel Drop-off Analysis", fontsize=13, fontweight="bold")
    for i, v in enumerate(drop_vals):
        axes[1].text(v + 0.5, i, f"{v:.1f}%",
                     va="center", fontsize=9, fontweight="bold")
    axes[1].set_xlim(0, max(drop_vals) * 1.3)

    path = save_chart(axes[0].figure, output_dir, "funnel_attribution.png")
    logger.info("Chart saved: %s", path)


def run_funnel(df: pd.DataFrame, output_dir: str,
               rfm: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Run full funnel analysis on pre-loaded data.

    Args:
        df: Cleaned transaction DataFrame.
        output_dir: Directory for output CSV and PNG files.
        rfm: Optional pre-computed RFM table (avoids redundant groupby).

    Returns:
        (funnel_table, dropoff_insights).
    """
    funnel = build_funnel(df, rfm=rfm)

    logger.info("Attribution Results:\n%s", funnel.to_string(index=False))

    insights = analyze_dropoff(funnel)
    logger.info("Key Drop-off Points:")
    for stage, info in insights.items():
        logger.info(
            "  %s → %s: %.1f%% retained, %.1f%% dropped (%s customers)",
            info["from"], info["to"], info["conversion"],
            info["dropoff"], f"{info['lost_customers']:,}",
        )

    plot_funnel(funnel, output_dir)

    funnel_path = Path(output_dir) / "funnel_table.csv"
    funnel.to_csv(funnel_path, index=False)
    logger.info("Table saved: %s", funnel_path)

    return funnel, insights


if __name__ == "__main__":
    from config import DATA_DIR, DATA_FILE, OUTPUT_DIR, setup_logging
    setup_logging()
    from data_preprocessing import load_and_clean  # type: ignore[import-not-found]
    df = load_and_clean(str(DATA_DIR / DATA_FILE))
    run_funnel(df, str(OUTPUT_DIR))
