from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "synthetic_jm_daily.json"


@pytest.fixture
def synthetic_payloads() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
