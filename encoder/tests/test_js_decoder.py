"""The viewer's JavaScript decoder must agree with the Python reference."""

import json
import re
import shutil
import subprocess

import pytest

from siren_qr import payload as P

from .conftest import ROOT

WEB = ROOT.parent / "docs"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def js_decode(digits: str) -> dict:
    out = subprocess.run(["node", str(WEB / "tests" / "decode_cli.mjs"), digits],
                         capture_output=True, text=True, check=True, timeout=30)
    return json.loads(out.stdout)


def test_js_matches_python(record, long_record, deff_record):
    for rec, with_name in ((record, True), (record, False), (long_record, True), (deff_record, True)):
        digits = P.encode(rec, include_name=with_name)
        js, py = js_decode(digits), P.decode(digits)
        assert js.pop("version") == 1
        assert js == json.loads(json.dumps(py))


def test_js_rejects_corrupt_digits(record):
    digits = P.encode(record)
    broken = digits[:-3] + ("000" if not digits.endswith("000") else "111")
    assert js_decode(broken)["error"] in {"checksum", "format"}


def test_alert_lists_match():
    js_list = re.search(r"ALERTS = \[(.*?)\]", (WEB / "decode.js").read_text(), re.S).group(1)
    assert re.findall(r'"(\w+)"', js_list) == P.ALERTS
