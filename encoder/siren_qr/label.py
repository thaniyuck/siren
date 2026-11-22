"""58 mm thermal label: readable summary on paper, trend URL in the QR.

The paper carries the essentials so the label still works with no signal.
The name (if any) is printed on paper only; it is never put in the URL.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from . import payload as P
from .qr import QrResult

WIDTH_PX = 384          # 58 mm printer at 203 dpi
BAND_ROWS = 128         # rows per ESC/POS raster command

_FONTS = {
    True: ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf"],
    False: ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf"],
}
SEX_TEXT = {"L": "L", "P": "P", None: "-"}


def _font(size: int, bold: bool = False):
    for path in _FONTS[bold]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def _hm(value: Any, tz=None) -> str:
    if value is None:
        return "-"
    return datetime.fromtimestamp(P._ts(value), tz=timezone.utc).astimezone(tz).strftime("%H:%M")


def _num(value, digits=0) -> str:
    return "-" if value is None else f"{value:.{digits}f}"


def _wrap(draw, line: str, font, width: int) -> list[str]:
    out, current = [], ""
    for word in line.split():
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not current:
            current = trial
        else:
            out.append(current)
            current = word
    return out + [current] if current else out or [""]


def render(record: dict[str, Any], result: QrResult, width: int = WIDTH_PX, tz=None) -> Image.Image:
    margin, inner = 8, width - 16
    small, regular, bold, big = _font(17), _font(20), _font(22, True), _font(46, True)
    canvas = Image.new("L", (width, 2000), 255)
    draw = ImageDraw.Draw(canvas)
    y = 4

    def text(line, font, gap=4):
        nonlocal y
        for chunk in _wrap(draw, line, font, inner):
            draw.text((margin, y), chunk, font=font, fill=0)
            y += font.size + gap

    text(f"SIREN  {record.get('code') or '-'}", bold)
    if record.get("simulated"):
        text("SIMULASI - bukan data pasien", small)

    colour = record.get("colour") or "BELUM ADA DATA"
    block = big.size + 18
    draw.rectangle([margin, y, width - margin, y + block], fill=0)
    box = draw.textbbox((0, 0), colour, font=big)
    draw.text(((width - (box[2] - box[0])) // 2, y + 6), colour, font=big, fill=255)
    y += block + 8

    news = record.get("news2")
    text(f"NEWS2 {_num(news)} ({record.get('news2_measured', 0)}/7)", regular)
    if record.get("name"):
        text(record["name"], bold)
    age = f"{record['age']} th" if record.get("age") is not None else "usia -"
    text(f"{age}, {SEX_TEXT.get(record.get('sex'), '-')}", regular)

    last = max(record.get("readings") or [{}], key=lambda r: P._ts(r["t"]) if r.get("t") else 0)
    if last.get("t"):
        text(f"Vital {_hm(last['t'], tz)}: N {_num(last.get('hr'))}  SpO2 {_num(last.get('spo2'))}  "
             f"RR {_num(last.get('rr'))}  S {_num(last.get('temp'), 1)}", small)
    cuffs = sorted(record.get("cuffs") or [], key=lambda c: P._ts(c["t"]))
    if cuffs:
        c = cuffs[-1]
        text(f"TD manset {_num(c.get('sys'))}/{_num(c.get('dia'))} ({_hm(c['t'], tz)})", small)
    else:
        text("TD manset belum diukur", small)
    ppg = [r for r in record.get("readings") or [] if r.get("sbp_ppg") is not None]
    if ppg:
        p = max(ppg, key=lambda r: P._ts(r["t"]))
        text(f"TD estimasi PPG {_num(p.get('sbp_ppg'))}/{_num(p.get('dbp_ppg'))} ({_hm(p['t'], tz)})", small)
    pain = record.get("pain")
    text(f"Kesadaran {(record.get('acvpu') or '-')[0].upper()}, O2 {'ya' if record.get('on_oxygen') else 'tidak'}, "
         f"nyeri {'-' if pain is None else pain}/10", small)
    started = record["readings"][0]["t"] if record.get("readings") else None
    text(f"Mulai {_hm(started, tz)}  Cetak {_hm(record.get('printed_at') or datetime.now(timezone.utc), tz)}", small)

    y += 6
    matrix = result.qr.make_image(fill_color="black", back_color="white").convert("L")
    scale = max(1, width // matrix.width)
    matrix = matrix.resize((matrix.width * scale, matrix.height * scale), Image.NEAREST)
    canvas.paste(matrix, ((width - matrix.width) // 2, y))
    y += matrix.height + 4

    text("Pindai QR untuk grafik tren (perlu internet).", small, gap=2)
    text("Alat bantu, bukan pengganti penilaian klinis.", small, gap=2)
    return canvas.crop((0, 0, width, y + 6))


def escpos_raster(image: Image.Image) -> bytes:
    """ESC/POS bytes (GS v 0 raster), understood by nearly every 58 mm receipt printer."""
    mono = ImageOps.invert(image.convert("L")).convert("1", dither=Image.Dither.NONE)
    if mono.width % 8:
        padded = Image.new("1", (mono.width + 8 - mono.width % 8, mono.height), 0)
        padded.paste(mono, (0, 0))
        mono = padded
    row_bytes = mono.width // 8
    out = bytearray(b"\x1b\x40")                       # ESC @ initialise
    for top in range(0, mono.height, BAND_ROWS):
        band = mono.crop((0, top, mono.width, min(top + BAND_ROWS, mono.height)))
        out += b"\x1d\x76\x30\x00"
        out += bytes([row_bytes & 0xFF, row_bytes >> 8, band.height & 0xFF, band.height >> 8])
        out += band.tobytes()
    out += b"\x1b\x64\x04"                             # feed past the tear bar
    return bytes(out)


def send(payload: bytes, device: str, baud: int = 9600) -> None:
    """Write to /dev/usb/lp0 directly, or to a serial port (COM5, /dev/rfcomm0) via pyserial."""
    if device.startswith(("/dev/usb/lp", "/dev/lp")) or device.endswith(".bin"):
        with open(device, "wb", buffering=0) as handle:
            handle.write(payload)
        return
    import serial  # optional dependency, only for serial and Bluetooth printers
    with serial.serial_for_url(device, baud, timeout=2, write_timeout=15) as port:
        port.write(payload)
        port.flush()
