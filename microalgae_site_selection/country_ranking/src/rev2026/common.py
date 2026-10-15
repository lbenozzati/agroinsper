"""Paths and shared schema for the 2026-10-15 revision."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "rev2026"
OUT = ROOT / "outputs" / "rev2026"
FROZEN = ROOT / "outputs" / "frozen_2026-10-14"

# minimum schema per evidence cell (brief §6) – extended with value_low/value_high and absence_type
CELL_COLS = ["metric_id", "entity", "entity_type", "niche", "sku", "value", "value_low", "value_high", "unit",
             "start_year", "end_year", "as_of_date", "source_id", "page_or_table", "evidence_type", "status",
             "absence_type", "formula", "verification_level", "notes"]


def load_config() -> dict:
    with open(ROOT / "config_rev2026.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)
