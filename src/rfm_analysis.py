"""
RFM Analysis: Recency, Frequency, Monetary customer segmentation.
Uses quintile scoring (1-5) and maps to 10 standard RFM segments.
"""
import logging
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .plotting import PALETTE_10, save_chart, plt
except ImportError:
    from plotting import PALETTE_10, save_chart, plt  # type: ignore[no-redef]

logger = logging.getLogger(__name__)


# ── Core RFM computation ──────────────────────────────────────────────

def _qcut_score(series: pd.Series, labels: list[int], *,
                rank: bool = False) -> pd.Series:
    """Quintile-cut a series with tie handling and low-variance guarding.

    Args:
        series: Values to score.
        labels: 5-element label list.
        rank: If True, rank-then-cut (for tied Frequency/Monetary data).

    Returns:
        Integer Series with values matching ``labels``.
    """
    if series.nunique() < 5:
        logger.warning("%s has <%d unique values; quintile scoring degraded",
                       series.name, 5)
    if rank:
        series = series.rank(method="first")
    return pd.qcut(series, 5, labels=labels, duplicates="drop").astype(int)


def compute_rfm(df: pd.DataFrame, reference_date: pd.Timestamp) -> pd.DataFrame:
    """Compute Recency, Frequency, Monetary metrics per customer.

    Args:
        df: Cleaned transaction DataFrame.
        reference_date: Reference point for recency (max(InvoiceDate) + 1 day).

    Returns:
        DataFrame with columns: CustomerID, Recency, Frequency, Monetary.
    """
    rfm = df.groupby("CustomerID").agg(
        Recency=("InvoiceDate", lambda x: (reference_date - x.max()).days),
        Frequency=("InvoiceNo", "nunique"),
        Monetary=("Revenue", "sum"),
    ).reset_index()
    rfm.columns = ["CustomerID", "Recency", "Frequency", "Monetary"]
    return rfm


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    """Assign quintile scores 1-5 to each RFM dimension.

    Recency: lower days → higher score (5=best).  Frequency & Monetary:
    higher value → higher score.  Rank-then-qcut handles tied data points.
    """
    rfm["R_Score"] = _qcut_score(rfm["Recency"],   [5, 4, 3, 2, 1])
    rfm["F_Score"] = _qcut_score(rfm["Frequency"], [1, 2, 3, 4, 5], rank=True)
    rfm["M_Score"] = _qcut_score(rfm["Monetary"],  [1, 2, 3, 4, 5], rank=True)

    rfm["RFM_Score"] = rfm["R_Score"] + rfm["F_Score"] + rfm["M_Score"]
    return rfm


def segment_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    """Map RFM scores to named customer segments via vectorised conditions.

    Rules are evaluated top-to-bottom (first match wins).  ``np.select`` is
    ~10× faster than ``df.apply(axis=1)`` on >10k rows.
    """
    conditions = [
        rfm["RFM_Score"] >= 13,
        rfm["RFM_Score"] >= 11,
        (rfm["RFM_Score"] >= 9) & (rfm["R_Score"] >= 4),
        (rfm["RFM_Score"] >= 9) & (rfm["F_Score"] >= 4),
        rfm["RFM_Score"] >= 9,
        (rfm["RFM_Score"] >= 7) & (rfm["R_Score"] >= 4),
        (rfm["RFM_Score"] >= 7) & (rfm["F_Score"] >= 3),
        rfm["RFM_Score"] >= 7,
        (rfm["RFM_Score"] >= 5) & (rfm["R_Score"] >= 3),
        rfm["RFM_Score"] >= 5,
    ]
    choices = [
        "Champions", "Loyal Customers",
        "Potential Loyalists", "At Risk", "Needs Attention",
        "New Customers", "About to Sleep", "Hibernating",
        "Promising", "Lost",
    ]
    rfm["Segment"] = np.select(conditions, choices, default="Lost")
    return rfm


# ── Summarisation & visualisation ─────────────────────────────────────

def summarize_segments(rfm: pd.DataFrame) -> pd.DataFrame:
    """Return per-segment summary statistics."""
    summary = rfm.groupby("Segment").agg(
        Customers=("CustomerID", "count"),
        Avg_Recency=("Recency", "mean"),
        Avg_Frequency=("Frequency", "mean"),
        Avg_Monetary=("Monetary", "mean"),
        Total_Revenue=("Monetary", "sum"),
        Pct_Revenue=("Monetary", lambda x: x.sum() / rfm["Monetary"].sum() * 100),
    ).sort_values("Total_Revenue", ascending=False)

    round_map = {
        "Avg_Recency": 1, "Avg_Frequency": 1, "Avg_Monetary": 0,
        "Total_Revenue": 0, "Pct_Revenue": 1,
    }
    for col, decimals in round_map.items():
        summary[col] = summary[col].round(decimals)

    return summary


def plot_rfm(rfm: pd.DataFrame, output_dir: str) -> None:
    """Generate RFM visualisation: pie chart + revenue bar chart.

    Small segments (<3% of customers) are merged into "Others".
    """
    seg_counts = rfm["Segment"].value_counts()

    # Merge tiny segments for readability
    threshold = 0.03 * seg_counts.sum()
    main_segs = seg_counts[seg_counts >= threshold]
    other_count = seg_counts[seg_counts < threshold].sum()
    if other_count > 0:
        main_segs = pd.concat([main_segs, pd.Series({"Others": other_count})])

    _, axes = plt.subplots(1, 2, figsize=(14, 5))

    # ── Pie chart ──
    axes[0].pie(
        main_segs.values, labels=main_segs.index, autopct="%1.1f%%",
        colors=PALETTE_10[:len(main_segs)], startangle=140,
        textprops={"fontsize": 9},
    )
    axes[0].set_title("RFM Customer Segmentation", fontsize=13, fontweight="bold")

    # ── Revenue bar chart ──
    seg_rev = rfm.groupby("Segment")["Monetary"].sum().sort_values()
    bars = axes[1].barh(seg_rev.index, seg_rev.values / 1e6,
                        color="#3498db", edgecolor="white")
    axes[1].set_xlabel("Total Revenue (Million GBP)", fontsize=11)
    axes[1].set_title("Revenue by Segment", fontsize=13, fontweight="bold")
    for bar, val in zip(bars, seg_rev.values):
        axes[1].text(
            bar.get_width() + 0.01, bar.get_y() + bar.get_height() / 2,
            f"{val/1e6:.2f}M", va="center", fontsize=8,
        )

    path = save_chart(axes[0].figure, output_dir, "rfm_segments.png")
    logger.info("Chart saved: %s", path)


# ── Entry point ───────────────────────────────────────────────────────

def run_rfm(df: pd.DataFrame, output_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run full RFM pipeline on pre-loaded data."""
    ref_date = df["InvoiceDate"].max() + pd.Timedelta(days=1)
    logger.info("Reference date: %s", ref_date.date())

    rfm = compute_rfm(df, ref_date)
    rfm = score_rfm(rfm)
    rfm = segment_rfm(rfm)

    summary = summarize_segments(rfm)
    logger.info("Segment Summary:\n%s", summary.to_string())

    plot_rfm(rfm, output_dir)

    rfm_path = Path(output_dir) / "rfm_table.csv"
    rfm.to_csv(rfm_path, index=False)
    logger.info("Table saved: %s", rfm_path)

    return rfm, summary


if __name__ == "__main__":
    from config import DATA_DIR, DATA_FILE, OUTPUT_DIR, setup_logging
    setup_logging()
    # Import directly (not via .) when run as script
    from data_preprocessing import load_and_clean  # type: ignore[import-not-found]
    df = load_and_clean(str(DATA_DIR / DATA_FILE))
    run_rfm(df, str(OUTPUT_DIR))
