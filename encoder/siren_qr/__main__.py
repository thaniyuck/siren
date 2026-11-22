"""Command line.

    python -m siren_qr examples/patient_deteriorating.json --base-url https://siren.my.id/ --png label.png
    python -m siren_qr record.json --base-url https://siren.my.id/ --escpos /dev/usb/lp0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import label, qr


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="siren_qr", description="Make the SIREN handover label QR.")
    ap.add_argument("record", type=Path, help="patient record JSON (see README)")
    ap.add_argument("--base-url", default=os.getenv("SIREN_QR_BASE_URL", "https://thaniyuck.github.io/siren/"),
                    help="viewer address (default https://thaniyuck.github.io/siren/) (env SIREN_QR_BASE_URL)")
    ap.add_argument("--png", type=Path, help="save the label as PNG")
    ap.add_argument("--escpos", help="print to a device: /dev/usb/lp0, /dev/rfcomm0, COM5")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--no-name", action="store_true", help="leave the name out of the QR (still printed on paper)")
    ap.add_argument("--max-version", type=int, default=qr.MAX_VERSION,
                    help=f"largest QR version (default {qr.MAX_VERSION}; 12 = bigger modules, coarser trend)")
    args = ap.parse_args(argv)

    record = json.loads(args.record.read_text(encoding="utf-8"))
    result = qr.make(record, args.base_url, max_version=args.max_version, include_name=not args.no_name)
    print(result.url)
    dots = label.WIDTH_PX // (result.qr.modules_count + 8)
    print(f"QR version {result.version} ({dots * 0.125:.2f} mm modules), {result.points} points every "
          f"{result.step_s} s, {len(result.url)} characters", file=sys.stderr)

    if args.png or args.escpos:
        image = label.render(record, result)
        if args.png:
            image.save(args.png)
            print(f"label saved to {args.png}", file=sys.stderr)
        if args.escpos:
            label.send(label.escpos_raster(image), args.escpos, args.baud)
            print(f"label sent to {args.escpos}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
