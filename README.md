# SIREN QR

The handover label QR for SIREN. The ambulance console stays offline. At handover it prints a 58 mm label whose QR code is a web address with the whole transport record packed into it. A nurse or doctor scans it and the phone shows the triage summary and trend graphs (NEWS2, HR, SpO2, RR, temperature, cuff BP).

```
console (offline)                      phone (online, or offline after first visit)
record -> 1 point/min -> bytes -> deflate -> digits -> QR
https://siren.my.id/#5377028445421508040137676941...   -> viewer decodes in the browser
                    └── fragment: never sent to any server
```

## What is in this folder

| Path | What it is |
|---|---|
| `encoder/siren_qr/payload.py` | Packs a record into digits and back (format v1, spec in the docstring) |
| `encoder/siren_qr/qr.py` | Builds the URL and the QR; widens the trend step until the QR fits version 12 |
| `encoder/siren_qr/label.py` | Draws the 58 mm label and makes ESC/POS printer bytes |
| `encoder/siren_qr/__main__.py` | Command line |
| `encoder/examples/` | Two made-up patients (40 min and 150 min transports) and the script that makes them |
| `encoder/tests/` | 18 pytest tests, including scanning the printed label back and checking the JS decoder |
| `docs/` | The viewer site. Static files only; GitHub Pages publishes this folder |
| `docs/decode.js` | Same format in JavaScript; used by the page and by the tests |
| `docs/sw.js` | Offline cache, so the page opens with no signal after the first visit |

## Quick start (Windows or Orange Pi)

```bash
cd encoder
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                       # 18 passed (the JS test needs Node 18+)

python -m siren_qr examples/patient_deteriorating.json --png label.png
# local viewer instead of the live site:
python -m siren_qr examples/patient_deteriorating.json --base-url http://localhost:8000/
```

It prints the URL, then a line such as `QR version 11, 40 points every 60 s`.

To see the viewer on your laptop, open a second terminal:

```bash
cd docs
python -m http.server 8000
```

Paste the printed URL into the browser. To test on a phone you need the site online (next section), because phones block the offline cache on plain `http://` addresses other than localhost.

Printing on the real printer:

```bash
python -m siren_qr record.json --base-url https://siren.my.id/ --escpos /dev/usb/lp0   # USB
python -m siren_qr record.json --base-url https://siren.my.id/ --escpos /dev/rfcomm0   # Bluetooth
python -m siren_qr record.json --base-url https://siren.my.id/ --escpos COM5           # Windows
```

You can also set the address once with the environment variable `SIREN_QR_BASE_URL`. Label times use the console's system time zone, so set the Orange Pi to Asia/Jakarta.

## Putting the viewer online (GitHub Pages)

1. Push this folder to `github.com/thaniyuck/siren` (public repository).
2. Settings → Pages → Source "Deploy from a branch", branch `main`, folder `/docs`.
3. The site is then at `https://thaniyuck.github.io/siren/`, which is also the encoder's default `--base-url`.
4. With your own domain, add it under Settings → Pages → Custom domain. At your registrar, add a CNAME record from `siren` (or `www`) to `<account>.github.io`. Tick "Enforce HTTPS" once the certificate is ready (can take up to a day).
5. Use the final address as `--base-url`. **Do not change it after you start printing**, because every printed label points to it.

When you change the viewer, bump `CACHE` in `docs/sw.js` so phones pick up the new files.

## Record format (input JSON)

```json
{
  "code": "SRN-261120-004",
  "name": "Rina Marlina",
  "age": 67, "sex": "P",
  "complaint": "Jatuh dari motor, nyeri paha kanan",
  "unit": "SIREN-01",
  "acvpu": "confusion", "on_oxygen": true, "pain": 7,
  "start_colour": "KUNING", "colour": "MERAH", "worst_colour": "MERAH",
  "news2": 14, "news2_measured": 7,
  "alerts": ["shock_index", "sbp_low"],
  "simulated": false, "handed_over": false,
  "printed_at": "2026-11-20T09:42:20+07:00",
  "cuffs": [{"t": "2026-11-20T09:02:00+07:00", "sys": 124, "dia": 78}],
  "readings": [{"t": "2026-11-20T09:02:00+07:00", "hr": 92.4, "spo2": 96.1, "rr": 18.2,
                "temp": 36.6, "news2": 1, "colour": "HIJAU"}]
}
```

- Every field is optional. Unknown values can be `null`.
- `sex` is `"L"` or `"P"`. `colour` values are `"HIJAU"`, `"KUNING"` or `"MERAH"`.
- `readings` can be the raw 10 s snapshots. The encoder groups them itself.
- `name` is printed on the paper label only. It is never put in the URL.
- `alerts` must come from this list: `shock_index`, `news2_rise`, `spo2_low`, `rr_high`, `rr_low`, `hr_high`, `hr_low`, `sbp_low`, `temp_high`, `temp_low`, `new_confusion`, `bp_trend`.
- Text fields are clipped to code 24, unit 16 and complaint 48 bytes.

## Design decisions

- **Data after `#`.** Browsers never send the URL fragment to the server, so the server only hosts a static page and never sees, logs or stores patient data. The page has `noindex`, `no-referrer` and a strict content security policy.
- **Digits, not base64.** QR codes have a numeric mode that stores 3 digits in 10 bits, about 25% denser than base64 in byte mode. The URL prefix goes in byte mode and the digits in numeric mode, as two segments of one QR.
- **One point per minute.** Up to 60 points. Longer transports use wider steps (2, 3 min…). If the QR would still exceed version 12, the step doubles until it fits. Each point holds the **median** of the vitals, which ignores motion spikes, and the **highest** NEWS2 and category, so the trend never hides a moment flagged in the ambulance.
- **Version 12 maximum.** On 384 dots that keeps 5 dots (0.63 mm) per module, which phone cameras read reliably. The test transports give version 11 (40 min) and 12 (150 min).
- **CRC32 check.** A misread or cut-off URL shows "pindai ulang" instead of wrong numbers.
- **Format version byte.** Labels printed now keep opening after the viewer changes. Only append to the alert list; never reorder it.
- **The paper still works alone.** The label prints the category, NEWS2, last vitals, cuff BP and consciousness as text, for when nobody has signal.
- **No name in the URL.** Under UU 27/2022 Pasal 4(2), health data is specific personal data. The URL also stays in the phone's browser history.

## Size (example records, base `https://siren.my.id/`)

| Record | Points | QR version | Module size |
|---|---|---|---|
| 40 min transport | 40 × 1 min | 11 | 0.63 mm |
| 150 min transport | 51 × 3 min | 12 | 0.63 mm |

Shorter domains help a little. `https://siren.my.id/` gives version 11 for the 40 min case; `https://<account>.github.io/siren-qr/` gives 12.

## Testing on real phones (before the demo)

- [ ] Print the example label. Scan it with at least 3 phones (one older Android, one iPhone) at 10 to 30 cm, using the built-in camera app.
- [ ] Check the page shows the same category, NEWS2 and last vitals as the paper.
- [ ] Open the page once, switch to aeroplane mode, scan again. The page should still open.
- [ ] Cover part of the QR or crease the label. You should see the "pindai ulang" message or a correct page, never wrong numbers.
- [ ] Try WhatsApp's and Google Lens' scanners too; some in-app browsers are old.

## Limitations and future work

- **Anyone can make a URL.** The CRC catches scan errors, not forgery. A digital signature (Ed25519, 64 bytes, about 1 to 2 more QR versions) with the public key in the page would prove a label came from a SIREN console.
- **Anyone who scans the label can read it.** The same is true of the printed text. Encrypting the payload would need a key the hospital holds, which is out of scope for the capstone.
- **Browser support.** The page needs `DecompressionStream("deflate-raw")`: Chrome or Android WebView 103+, Safari 16.4+ (iOS 16.4), Firefox 113+. Older browsers get a clear message.
- **Snapshot, not monitoring.** The page says when the data ends. It does not update.
