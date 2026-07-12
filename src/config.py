"""Shared project configuration — paths, constants, logging setup."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python ≥3.11
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

# ── Project root ──
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DATA_FILE = "Online Retail.xlsx"

# ── Business constants ──
MIN_LIFESPAN_DAYS = 30  # floor for single-purchase customers (avoid freq inflation)

# ── Logging ──
LOG_FORMAT = "%(levelname)-7s | %(name)-22s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger.  Call once from main()."""
    logging.basicConfig(level=level, format=LOG_FORMAT)


# ── Business params loader ────────────────────────────────────────────


@dataclass
class BusinessParams:
    """All tunable business thresholds, loaded from ``business_params.toml``."""

    # Funnel
    repeat_buyer_threshold: int = 2
    regular_buyer_threshold: int = 5
    high_value_quantile: float = 0.80
    vip_quantile: float = 0.95

    # CLV
    min_lifespan_days: int = 30
    freq_cap: int = 10
    projection_months: int = 12


def load_business_params(path: str | Path) -> BusinessParams:
    """Load business thresholds from a TOML file."""
    with open(path, "rb") as fh:
        raw: dict[str, Any] = tomllib.load(fh)

    funnel = raw.get("funnel", {})
    clv = raw.get("clv", {})

    return BusinessParams(
        repeat_buyer_threshold=int(funnel.get("repeat_buyer_threshold", 2)),
        regular_buyer_threshold=int(funnel.get("regular_buyer_threshold", 5)),
        high_value_quantile=float(funnel.get("high_value_quantile", 0.80)),
        vip_quantile=float(funnel.get("vip_quantile", 0.95)),
        min_lifespan_days=int(clv.get("min_lifespan_days", 30)),
        freq_cap=int(clv.get("freq_cap", 10)),
        projection_months=int(clv.get("projection_months", 12)),
    )
