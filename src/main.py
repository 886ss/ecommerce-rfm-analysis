"""
E-Commerce Data Analysis — CLI Entry Point
===========================================
Usage:
    python -m src.main --data ./data/my_orders.xlsx
    python -m src.main --data ./data/my_orders.xlsx --no-plot
    python -m src.main --data ./data/my_orders.xlsx --only rfm
    python -m src.main --data ./data/my_orders.xlsx \\
        --mapping ./column_mapping.toml --params ./business_params.toml
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

try:
    from .clv_estimation import run_clv
    from .config import (
        DATA_DIR,
        DATA_FILE,
        OUTPUT_DIR,
        BusinessParams,
        load_business_params,
        setup_logging,
    )
    from .data_preprocessing import load_and_clean
    from .funnel_attribution import run_funnel
    from .rfm_analysis import run_rfm
    from .schema import ColumnMapping, load_column_mapping
except ImportError:
    from clv_estimation import run_clv  # type: ignore[import-not-found, no-redef]
    from config import (  # type: ignore[import-not-found, no-redef]
        DATA_DIR,
        DATA_FILE,
        OUTPUT_DIR,
        BusinessParams,
        load_business_params,
        setup_logging,
    )
    from data_preprocessing import load_and_clean  # type: ignore[import-not-found, no-redef]
    from funnel_attribution import run_funnel  # type: ignore[import-not-found, no-redef]
    from rfm_analysis import run_rfm  # type: ignore[import-not-found, no-redef]
    from schema import (  # type: ignore[import-not-found, no-redef]
        ColumnMapping,
        load_column_mapping,
    )

logger = logging.getLogger("main")

# ── CLI ────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="E-Commerce RFM + Funnel + CLV Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python -m src.main --data ./data/my_orders.xlsx\n"
            "  python -m src.main --data ./data/my_orders.xlsx --only rfm\n"
            "  python -m src.main --data ./data/my_orders.xlsx"
            " --mapping ./column_mapping.toml"
        ),
    )
    p.add_argument(
        "--data", type=str, default=None,
        help="Path to the input Excel / CSV file (required).",
    )
    p.add_argument(
        "--output", type=str, default=None,
        help="Output directory for CSVs and PNGs (default: ./output).",
    )
    p.add_argument(
        "--mapping", type=str, default=None,
        help="Path to column_mapping.toml (for non-UCI datasets).",
    )
    p.add_argument(
        "--params", type=str, default=None,
        help="Path to business_params.toml (custom thresholds).",
    )
    p.add_argument(
        "--no-plot", action="store_true",
        help="Skip chart generation (useful for headless / CI environments).",
    )
    p.add_argument(
        "--only", type=str, choices=["rfm", "funnel", "clv"], default=None,
        help="Run only one analysis module instead of all three.",
    )
    p.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    return p


# ── Main ───────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    """Parse CLI args, load configs, and run the analysis pipeline."""
    args = _build_parser().parse_args(argv)

    # ── Resolve paths ──
    data_path = Path(args.data) if args.data else DATA_DIR / DATA_FILE
    output_dir = Path(args.output) if args.output else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Logging ──
    setup_logging(level=getattr(logging, args.log_level))

    # ── Banner ──
    logger.info("=" * 60)
    logger.info("  E-Commerce Data Analysis: RFM + Funnel + CLV")
    logger.info("  Data: %s", data_path)
    logger.info("  Output: %s", output_dir)
    logger.info("=" * 60)

    # ── Guard: data must exist ──
    if not data_path.exists():
        logger.error("Data file not found: %s", data_path)
        logger.error(
            "Download the UCI Online Retail dataset from "
            "https://archive.ics.uci.edu/dataset/352/online+retail"
        )
        sys.exit(1)

    # ── Load optional configs ──
    column_mapping: ColumnMapping | None = None
    if args.mapping:
        logger.info("Loading column mapping from %s", args.mapping)
        column_mapping = load_column_mapping(args.mapping)

    biz = BusinessParams()
    if args.params:
        logger.info("Loading business params from %s", args.params)
        biz = load_business_params(args.params)

    # ── Load data (once) ──
    df = load_and_clean(str(data_path), mapping=column_mapping)

    # ── RFM is the foundation — always computed, selectively reported ──
    rfm, rfm_summary = run_rfm(df, str(output_dir))

    run_all = args.only is None

    if run_all or args.only == "funnel":
        logger.info("=" * 60)
        logger.info("  STEP %s: Funnel Attribution Analysis",
                    "2/3" if run_all else "")
        logger.info("=" * 60)
        _funnel, _insights = run_funnel(
            df, str(output_dir), rfm=rfm,
            repeat_buyer_threshold=biz.repeat_buyer_threshold,
            regular_buyer_threshold=biz.regular_buyer_threshold,
            high_value_quantile=biz.high_value_quantile,
            vip_quantile=biz.vip_quantile,
        )

    if run_all or args.only == "clv":
        logger.info("=" * 60)
        logger.info("  STEP %s: Customer Lifetime Value Estimation",
                    "3/3" if run_all else "")
        logger.info("=" * 60)
        _clv, _clv_summary = run_clv(df, rfm, str(output_dir))

    logger.info("=" * 60)
    logger.info("  ALL ANALYSES COMPLETE")
    logger.info("  Output files in: %s", output_dir)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
