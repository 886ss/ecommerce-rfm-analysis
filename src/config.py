"""Shared project configuration — paths, constants, logging setup."""
import logging
from pathlib import Path

# ── Project root ──
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
DATA_FILE = "Online Retail.xlsx"

# ── Business constants ──
MIN_LIFESPAN_DAYS = 30  # floor for single-purchase customers (avoid freq inflation)

# ── Logging (convenience: configure once at entry point) ──
LOG_FORMAT = "%(levelname)-7s | %(name)-22s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger.  Call once from main()."""
    logging.basicConfig(level=level, format=LOG_FORMAT)
