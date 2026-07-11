"""
E-Commerce Data Analysis — Main Entry Point
============================================
Usage:  python -m src.main
"""
import logging
import sys
from pathlib import Path

from .config import DATA_DIR, DATA_FILE, OUTPUT_DIR, setup_logging
from .data_preprocessing import load_and_clean
from .rfm_analysis import run_rfm
from .funnel_attribution import run_funnel
from .clv_estimation import run_clv

logger = logging.getLogger("main")


def main() -> None:
    """Orchestrate the full analysis pipeline — load once, analyze three ways."""
    setup_logging()

    data_path = DATA_DIR / DATA_FILE
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("  E-Commerce Data Analysis: RFM + Funnel + CLV")
    logger.info("  Dataset: UCI Online Retail")
    logger.info("=" * 60)

    if not data_path.exists():
        logger.error("Data file not found: %s", data_path)
        logger.error(
            "Download from: "
            "https://archive.ics.uci.edu/ml/datasets/online+retail"
        )
        sys.exit(1)

    df = load_and_clean(str(data_path))

    # ── Step 1: RFM Segmentation ──
    logger.info("=" * 60)
    logger.info("  STEP 1/3: RFM Customer Segmentation")
    logger.info("=" * 60)
    rfm, _rfm_summary = run_rfm(df, str(output_dir))

    # ── Step 2: Funnel Attribution (reuses RFM to avoid redundant groupby) ──
    logger.info("=" * 60)
    logger.info("  STEP 2/3: Funnel Attribution Analysis")
    logger.info("=" * 60)
    _funnel, _insights = run_funnel(df, str(output_dir), rfm=rfm)

    # ── Step 3: CLV Estimation (reuses pre-computed RFM) ──
    logger.info("=" * 60)
    logger.info("  STEP 3/3: Customer Lifetime Value Estimation")
    logger.info("=" * 60)
    _clv, _clv_summary = run_clv(df, rfm, str(output_dir))

    logger.info("=" * 60)
    logger.info("  ALL ANALYSES COMPLETE")
    logger.info("  Output files in: %s", output_dir)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
