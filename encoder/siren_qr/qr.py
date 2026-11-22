"""Viewer URL and QR code for one patient.

The QR holds two segments: the base URL in byte mode and the payload digits
in numeric mode. Phone scanners join them back into one URL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import qrcode
from qrcode.util import MODE_8BIT_BYTE, MODE_NUMBER, QRData

from . import payload as P

# 58 mm printer, 384 dots: version 12 is 65 modules + 8 quiet = 73, so 5 dots
# (0.63 mm) per module. Phones read that reliably at label distance.
MAX_VERSION = 12
ERROR_CORRECTION = qrcode.constants.ERROR_CORRECT_M


@dataclass
class QrResult:
    url: str
    qr: qrcode.QRCode
    step_s: int
    points: int

    @property
    def version(self) -> int:
        return self.qr.version


def _normalise_base(base_url: str) -> str:
    base = base_url.split("#", 1)[0]
    if not base.startswith(("https://", "http://")):
        raise ValueError("base URL must start with https:// (or http:// for local testing)")
    return base


def build_qr(base: str, digits: str) -> qrcode.QRCode:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECTION, border=4, box_size=1)
    qr.add_data(QRData(base + "#", MODE_8BIT_BYTE))
    qr.add_data(QRData(digits, MODE_NUMBER))
    qr.make(fit=True)
    return qr


def make(record: dict[str, Any], base_url: str, max_version: int = MAX_VERSION) -> QrResult:
    """Fit the trend into the QR: start at one point per minute, widen the step if needed."""
    base = _normalise_base(base_url)
    readings = record.get("readings") or []
    step = None
    for _ in range(20):
        trend = P.bucket(readings, step_s=step)
        digits = P.encode(record, trend)
        qr = build_qr(base, digits)
        if qr.version <= max_version:
            return QrResult(f"{base}#{digits}", qr, trend.step_s, len(trend.points))
        step = trend.step_s * 2 if trend.points else 60
    raise P.PayloadError("record does not fit in the QR even at a coarse step; shorten the text fields")
