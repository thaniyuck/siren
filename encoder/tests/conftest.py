import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EXAMPLES = ROOT / "examples"
BASE = "https://siren.my.id/"


@pytest.fixture
def record():
    return json.loads((EXAMPLES / "patient_deteriorating.json").read_text(encoding="utf-8"))


@pytest.fixture
def long_record():
    return json.loads((EXAMPLES / "patient_long_transport.json").read_text(encoding="utf-8"))


@pytest.fixture
def deff_record():
    return json.loads((EXAMPLES / "patient_deffandio.json").read_text(encoding="utf-8"))
