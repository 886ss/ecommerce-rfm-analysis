"""Column-name mapping and input-data validation.

Decouples raw-data column names from the internal standard names used
throughout the analysis modules.  Users edit `column_mapping.toml` once
instead of touching five source files.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

try:
    import tomllib  # Python ≥3.11
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

logger = logging.getLogger(__name__)

# ── Data structures ───────────────────────────────────────────────────


@dataclass
class ColumnMapping:
    """Maps a user's Excel column names to our internal standard names.

    ``required`` fields must exist in the input file or validation fails.
    ``optional`` fields are used if present, silently skipped otherwise.
    """

    customer_id: str
    invoice_no: str
    invoice_date: str
    quantity: str
    unit_price: str

    # Optional columns
    stock_code: str | None = None
    description: str | None = None
    country: str | None = None

    # Cancel-detection config
    cancel_mode: str = "prefix"
    cancel_value: str = "C"

    @property
    def required_map(self) -> dict[str, str]:
        """Return {internal_name: user_column_name} for required columns."""
        return {
            "CustomerID": self.customer_id,
            "InvoiceNo": self.invoice_no,
            "InvoiceDate": self.invoice_date,
            "Quantity": self.quantity,
            "UnitPrice": self.unit_price,
        }

    @property
    def optional_map(self) -> dict[str, str]:
        """Return {internal_name: user_column_name} for optional columns."""
        mapping: dict[str, str] = {}
        if self.stock_code:
            mapping["StockCode"] = self.stock_code
        if self.description:
            mapping["Description"] = self.description
        if self.country:
            mapping["Country"] = self.country
        return mapping


# ── I/O ───────────────────────────────────────────────────────────────


def load_column_mapping(path: str | Path) -> ColumnMapping:
    """Load column-name mapping from a TOML config file.

    Example file (`column_mapping.toml`)::

        [required]
        customer_id  = "user_id"
        invoice_no   = "order_id"
        invoice_date = "created_at"
        quantity     = "qty"
        unit_price   = "price"

    """
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    req = raw["required"]
    opt = raw.get("optional", {})
    cancel = raw.get("cancel_detection", {})

    return ColumnMapping(
        customer_id=req["customer_id"],
        invoice_no=req["invoice_no"],
        invoice_date=req["invoice_date"],
        quantity=req["quantity"],
        unit_price=req["unit_price"],
        stock_code=opt.get("stock_code"),
        description=opt.get("description"),
        country=opt.get("country"),
        cancel_mode=cancel.get("mode", "prefix"),
        cancel_value=cancel.get("value", "C"),
    )


# ── Validation ────────────────────────────────────────────────────────


def validate_columns(df: pd.DataFrame, mapping: ColumnMapping) -> None:
    """Check that all required user columns exist in the DataFrame.

    Raises:
        KeyError: If any required column is missing, with a
            human-readable message listing what's missing.
    """
    missing: list[str] = []
    for internal, user_col in mapping.required_map.items():
        if user_col not in df.columns:
            missing.append(f"  • '{user_col}' (maps to internal '{internal}')")

    if missing:
        msg = (
            "Missing required columns in input data:\n"
            + "\n".join(missing)
            + "\n\nCheck your column_mapping.toml — the file should map "
            + "your Excel column names to the five required internal names."
        )
        raise KeyError(msg)

    logger.info("Column validation passed — all %d required columns present",
                len(mapping.required_map))


def apply_mapping(df: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Rename user columns → internal standard names (in-place on a copy)."""
    # Build reverse map: user_col → internal_name
    rename: dict[str, str] = {}
    for internal, user_col in mapping.required_map.items():
        rename[user_col] = internal
    for internal, user_col in mapping.optional_map.items():
        if user_col in df.columns:
            rename[user_col] = internal

    return df.rename(columns=rename)
