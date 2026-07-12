"""
CLV Estimation: Customer Lifetime Value estimation using historical revenue
and a simple predictive model.
"""
import logging
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .plotting import SEGMENT_COLORS, plt, save_chart
    from .rfm_analysis import compute_rfm, score_rfm, segment_rfm
except ImportError:
    from plotting import (  # type: ignore[import-not-found, no-redef]
        SEGMENT_COLORS,
        plt,
        save_chart,
    )
    from rfm_analysis import (  # type: ignore[import-not-found, no-redef]
        compute_rfm,
        score_rfm,
        segment_rfm,
    )

logger = logging.getLogger(__name__)


def estimate_clv(
    df: pd.DataFrame,
    rfm: pd.DataFrame,
    *,
    min_lifespan_days: int = 30,
    freq_cap: int = 10,
    projection_months: int = 12,
) -> pd.DataFrame:
    """Estimate CLV per customer via naive linear extrapolation.

    .. warning::
       This is a **simplified demonstration model**, not production-grade.
       Limitations include:

       - Assumes constant monthly purchase frequency for the projection
         period (no churn, no seasonality).
       - Caps monthly purchase frequency at ``freq_cap`` — an arbitrary
         guardrail, not a business rule.
       - No discount rate, no lifecycle stages.

       For production use, consider **BG/NBD** or **Pareto/NBD** from the
       ``lifetimes`` library.

    Args:
        df: Cleaned transaction DataFrame.
        rfm: Pre-computed RFM DataFrame (from ``run_rfm()``).
        min_lifespan_days: Floor for single-purchase customer lifespan,
            to prevent Purchase_Freq inflation.
        freq_cap: Maximum monthly purchase frequency for CLV projection.
        projection_months: Number of months to project forward.

    Returns:
        DataFrame with per-customer CLV metrics, merged with RFM segments.
    """
    # Group only for columns RFM doesn't already provide.
    cust = df.groupby("CustomerID").agg(
        Total_Items=("Quantity", "sum"),
        First_Purchase=("InvoiceDate", "min"),
        Last_Purchase=("InvoiceDate", "max"),
    ).reset_index()

    # Single merge — Monetary = total revenue, Frequency = total orders.
    clv = cust.merge(rfm, on="CustomerID", how="left")

    # ── Derived features (use RFM columns directly) ──
    clv["AOV"] = np.where(
        clv["Frequency"] > 0,
        clv["Monetary"] / clv["Frequency"],
        0.0,
    )
    clv["Lifespan_Days"] = (
        (clv["Last_Purchase"] - clv["First_Purchase"]).dt.days
    ).clip(lower=min_lifespan_days)
    clv["Purchase_Freq"] = clv["Frequency"] / (clv["Lifespan_Days"] / 30)

    # ── CLV estimates ──
    clv["Historical_CLV"] = clv["Monetary"]
    clv["Predictive_CLV_12m"] = (
        clv["AOV"] * clv["Purchase_Freq"].clip(upper=freq_cap) * projection_months
    )

    return clv


def summarize_clv_by_segment(clv: pd.DataFrame) -> pd.DataFrame:
    """Return per-segment CLV summary statistics."""
    summary = clv.groupby("Segment").agg(
        Customers=("CustomerID", "count"),
        Avg_Historical_CLV=("Historical_CLV", "mean"),
        Median_Historical_CLV=("Historical_CLV", "median"),
        Avg_Predictive_CLV_12m=("Predictive_CLV_12m", "mean"),
        Total_Historical_Revenue=("Historical_CLV", "sum"),
        Pct_of_Total_Revenue=(
            "Historical_CLV",
            lambda x: x.sum() / clv["Historical_CLV"].sum() * 100,
        ),
        Avg_AOV=("AOV", "mean"),
        Avg_Lifespan_Days=("Lifespan_Days", "mean"),
    ).sort_values("Avg_Historical_CLV", ascending=False)

    for col in [
        "Avg_Historical_CLV", "Median_Historical_CLV",
        "Avg_Predictive_CLV_12m", "Avg_AOV", "Total_Historical_Revenue",
        "Avg_Lifespan_Days",
    ]:
        summary[col] = summary[col].round(0)
    summary["Pct_of_Total_Revenue"] = summary["Pct_of_Total_Revenue"].round(1)

    return summary


def plot_clv(clv: pd.DataFrame, output_dir: str) -> None:
    """Generate CLV visualisation: boxplot + scatter by segment."""
    _, axes = plt.subplots(1, 2, figsize=(14, 5))

    # ── Boxplot: top-5 segments by count ──
    top_segs = clv["Segment"].value_counts().head(5).index.tolist()
    plot_data = clv[clv["Segment"].isin(top_segs)]
    plot_data = plot_data.assign(Log_CLV=np.log1p(plot_data["Historical_CLV"]))

    box_data = [
        plot_data.loc[plot_data["Segment"] == s, "Log_CLV"].values
        for s in top_segs
    ]
    axes[0].boxplot(
        box_data, patch_artist=True, showfliers=False,
        boxprops={"facecolor": "#3498db", "alpha": 0.7},
        medianprops={"color": "darkred", "linewidth": 2},
    )
    axes[0].set_xticklabels(top_segs)
    axes[0].set_title(
        "Historical CLV Distribution by Segment (log scale)",
        fontsize=11, fontweight="bold",
    )
    axes[0].set_ylabel("Log(1 + CLV)", fontsize=10)
    axes[0].tick_params(axis="x", rotation=20, labelsize=8)

    # ── Scatter: Recency vs CLV, coloured by segment ──
    for seg in top_segs:
        subset = plot_data[plot_data["Segment"] == seg]
        axes[1].scatter(
            subset["Recency"], subset["Log_CLV"],
            c=SEGMENT_COLORS.get(seg, "gray"), label=seg, alpha=0.5, s=15,
        )
    axes[1].set_xlabel("Recency (days)", fontsize=10)
    axes[1].set_ylabel("Log(1 + Historical CLV)", fontsize=10)
    axes[1].set_title("Recency vs CLV by Segment", fontsize=11, fontweight="bold")
    axes[1].legend(fontsize=7, loc="upper right", markerscale=2)

    path = save_chart(axes[0].figure, output_dir, "clv_analysis.png")
    logger.info("Chart saved: %s", path)


def run_clv(
    df: pd.DataFrame, rfm: pd.DataFrame, output_dir: str, *,
    no_plot: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run full CLV pipeline, reusing pre-computed RFM table."""
    clv = estimate_clv(df, rfm)
    summary = summarize_clv_by_segment(clv)

    logger.info("Segment CLV Summary:\n%s", summary.to_string())
    logger.info("Overall Metrics:")
    logger.info("  Avg Historical CLV: %s", f"{clv['Historical_CLV'].mean():,.0f}")
    logger.info("  Median Historical CLV: %s", f"{clv['Historical_CLV'].median():,.0f}")
    logger.info("  Total Revenue Captured: %s", f"{clv['Historical_CLV'].sum():,.0f}")
    logger.info("  Avg AOV: %.2f", clv["AOV"].mean())
    logger.info("  Avg Lifespan: %.0f days", clv["Lifespan_Days"].mean())

    if not no_plot:
        plot_clv(clv, output_dir)

    clv_path = Path(output_dir) / "clv_table.csv"
    clv.to_csv(clv_path, index=False)
    logger.info("Table saved: %s", clv_path)

    return clv, summary


if __name__ == "__main__":
    from config import (  # type: ignore[import-not-found]  # noqa: E501
        DATA_DIR,
        DATA_FILE,
        OUTPUT_DIR,
        setup_logging,
    )
    setup_logging()
    from data_preprocessing import load_and_clean  # type: ignore[import-not-found]

    df = load_and_clean(str(DATA_DIR / DATA_FILE))
    ref_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)
    rfm = segment_rfm(score_rfm(compute_rfm(df, ref_date)))
    run_clv(df, rfm, str(OUTPUT_DIR))
