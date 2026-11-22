# SIREN QR

The handover label QR for SIREN. The ambulance console stays offline. At handover it prints a 58 mm label whose QR code is a web address with the whole transport record packed into it. A nurse or doctor scans it and the phone shows the patient summary, the current and worst condition, and trend graphs (NEWS2, HR, SpO2, RR, temperature, PPG blood-pressure estimate and cuff BP).

```
console (offline)                                   phone (online, or offline after first visit)
record -> 1 point/min -> bytes -> deflate -> digits -> QR
https://thaniyuck.github.io/siren/#537702844542...   -> viewer decodes in the browser
                                  └── fragment: never sent to any server
```

- The console needs no internet at any point.
- The phone needs internet once, to download the viewer page (about 25 kB). The patient data after `#` is decoded on the phone and never sent anywhere.
- After one visit the phone keeps a copy of the page, so later labels open with no signal.
- The paper label also prints the key numbers as text, for when nobody has signal.

Live viewer: https://thaniyuck.github.io/siren/

---

## How to run

### 1. Install (once)

Needs Python 3.10 or newer. Node 18+ is optional (only for the JavaScript test).

Windows (PowerShell):
```powershell
cd D:\siren-qr\encoder
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Orange Pi or Linux:
```bash
cd ~/siren-qr/encoder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Each new terminal needs the `activate` line again before running anything below.

### 2. Check everything works

```powershell
python -m pytest -q
```
Expected: `27 passed`. Without Node the JavaScript test is skipped.

### 3. Make a label from a record (works offline)

```powershell
python -m siren_qr examples\patient_deffandio.json --png label.png
start label.png                 # Windows; on Linux: xdg-open label.png
```

The terminal shows the URL and a line such as
`QR version 13 (0.50 mm modules), 30 points every 60 s, 643 characters`.

The included examples:

| File | Patient | Story |
|---|---|---|
| `examples/patient_deffandio.json` | Deffandio, 22, L | Smoke inhalation, MERAH to HIJAU on oxygen, 30 min |
| `examples/patient_deteriorating.json` | Rina Marlina, 67, P | Bleeding after a motorbike fall, worsening shock, 40 min |
| `examples/patient_long_transport.json` | Rina Marlina, 67, P | Same story over 150 min |

To rebuild them: `python examples\make_example.py`.

### 4. Scan it

- Open `label.png` on the laptop screen and scan it with the phone camera. The phone needs internet the first time.
- To test offline viewing, scan once with internet, switch the phone to aeroplane mode, then scan again.
- **Don't copy the URL by selecting it in PowerShell.** It is 550 to 820 characters and the terminal wraps it, so a digit or two goes missing and the page shows "Data di QR tidak lengkap atau rusak". To open it on the laptop, copy it safely:
  ```powershell
  python -m siren_qr examples\patient_deffandio.json | Set-Clipboard
  ```
  Then paste into the browser with Ctrl+V.

### 5. Print on the thermal printer

```bash
python -m siren_qr record.json --escpos /dev/usb/lp0      # USB on the Orange Pi
python -m siren_qr record.json --escpos /dev/rfcomm0      # Bluetooth on the Orange Pi
python -m siren_qr record.json --escpos COM5              # Windows serial or Bluetooth port
```

After the first real print, scan the paper label with 2 or 3 phones. If it scans poorly, add `--max-version 12`. The QR modules get larger (0.63 mm) and the trend uses wider steps to fit.

### 6. Options

| Option | What it does |
|---|---|
| `--png FILE` | Save the label image |
| `--escpos DEVICE` | Send the label to a receipt printer |
| `--baud N` | Serial speed for `--escpos` (default 9600) |
| `--base-url URL` | Viewer address (default `https://thaniyuck.github.io/siren/`; env `SIREN_QR_BASE_URL`) |
| `--no-name` | Keep the name on paper only, not in the QR |
| `--max-version N` | Largest QR version (default 15; 12 gives bigger modules and a coarser trend) |

### 7. Use it from the console code (Python)

```python
from siren_qr import qr, label

result = qr.make(record, "https://thaniyuck.github.io/siren/")   # record = dict, format below
image = label.render(record, result)                               # PIL image, 384 px wide
label.send(label.escpos_raster(image), "/dev/usb/lp0")
print(result.url, result.version, result.step_s)
```

### 8. View on the laptop without the live site (optional)

Only needed to try viewer changes before pushing them.
```powershell
cd D:\siren-qr\docs
python -m http.server 8000
```
In a second terminal, make the URL with `--base-url http://localhost:8000/` and open it on the same laptop. Phones can't open `localhost`.

### 9. Update the live site

```powershell
cd D:\siren-qr
git add .
git commit -m "Describe the change"
git push
```
- GitHub Pages republishes `docs/` in 1 to 2 minutes (Actions tab, green tick).
- When you change files in `docs/`, bump `CACHE` in `docs/sw.js` (for example `siren-qr-v4` to `siren-qr-v5`) so phones fetch the new version.
- First-time setup: Settings, Pages, Deploy from a branch, branch `main`, folder `/docs`.
- If `git push` says "Password authentication is not supported", sign in through the browser window that Git opens, or run `gh auth login`.

---

## Record format (input JSON)

```json
{
  "code": "SRN-261122-011",
  "name": "Deffandio",
  "age": 22, "sex": "L",
  "complaint": "Sesak napas, terhirup asap kebakaran gedung",
  "unit": "SIREN-02",
  "acvpu": "alert", "on_oxygen": true, "pain": 3,
  "start_colour": "MERAH", "colour": "HIJAU", "worst_colour": "MERAH",
  "news2": 3, "news2_measured": 7,
  "alerts": ["spo2_low", "rr_high"],
  "simulated": false, "handed_over": false,
  "printed_at": "2026-11-22T14:35:15+07:00",
  "cuffs": [{"t": "2026-11-22T14:05:00+07:00", "sys": 138, "dia": 86}],
  "readings": [{"t": "2026-11-22T14:05:00+07:00", "hr": 124.2, "spo2": 89.1, "rr": 28.0,
                "temp": 37.2, "sbp_ppg": 137, "dbp_ppg": 86, "news2": 8, "colour": "MERAH"}]
}
```

- Every field is optional. Unknown values can be `null`.
- `sex` is `"L"` or `"P"`. Colours are `"HIJAU"`, `"KUNING"` or `"MERAH"`. `acvpu` can be the word or its first letter.
- `readings` can be the raw 10 s snapshots. The encoder groups them into one point per minute itself.
- `sbp_ppg` and `dbp_ppg` are the PPG model's blood-pressure estimate. Leave them `null` before the first cuff calibration and while the finger is off. NEWS2 must still use the cuff.
- `cuffs` holds the real cuff readings (the last 12 are kept).
- `alerts` must come from this list: `shock_index`, `news2_rise`, `spo2_low`, `rr_high`, `rr_low`, `hr_high`, `hr_low`, `sbp_low`, `temp_high`, `temp_low`, `new_confusion`, `bp_trend`.
- Text limits: code 24, unit 16, complaint 48, name 32 bytes.

---

## What is in this folder

| Path | What it is |
|---|---|
| `encoder/siren_qr/payload.py` | Packs a record into digits and back (format spec in the docstring) |
| `encoder/siren_qr/qr.py` | Builds the URL and the QR; widens the trend step until the QR fits |
| `encoder/siren_qr/label.py` | Draws the 58 mm label and makes ESC/POS printer bytes |
| `encoder/siren_qr/__main__.py` | Command line |
| `encoder/examples/` | Example records and the script that makes them |
| `encoder/tests/` | 27 pytest tests, including scanning the label image back and checking the JS decoder |
| `docs/` | The viewer site (static files). GitHub Pages publishes this folder |
| `docs/decode.js` | Same format in JavaScript, used by the page and the tests |
| `docs/sw.js` | Offline cache |

---

## Design decisions

- **Data after `#`.** Browsers never send the URL fragment to the server, so the server only hosts a static page and never sees, logs or stores patient data. The page has `noindex`, `no-referrer` and a strict content security policy.
- **Digits, not base64.** QR codes have a numeric mode (3 digits in 10 bits), about 25% denser than base64 in byte mode. The URL prefix is in byte mode, the digits in numeric mode, in one QR.
- **The trend step adapts to the transport length.** It starts at one point per minute, up to 60 points. Longer transports use wider steps (61 to 120 min becomes 2 min, 121 to 180 min becomes 3 min, and so on). If the QR would still exceed the version limit, the step widens one minute at a time (1, 2, 3, 4 …) until it fits, so the label always keeps the finest step that fits. Vitals and the PPG BP estimate use the **median** of the minute (ignores motion spikes). NEWS2 and category use the **highest** value in the minute, so the trend never hides a moment flagged in the ambulance.
- **PPG blood pressure is shown as an estimate.** It appears as a shaded band labelled "Estimasi PPG", with the cuff readings as solid dots on top. The page always shows both values. Category and NEWS2 come from the cuff, in line with the BP model evaluation (SBP does not meet ISO 81060-2 yet).
- **QR size.** Up to version 12 the modules are 5 printer dots (0.63 mm); versions 13 to 15 use 4 dots (0.50 mm). Adding the per-minute BP estimate needs version 13 or 14. In an image stress test, version 14 still decoded at normal size and with mild blur, but failed sooner than version 11 when shrunk and blurred. Test on real paper; `--max-version 12` is the fallback.
- **Current and worst condition.** "Saat ini" is the last minute. "Terburuk" is the first minute with the highest NEWS2, with the cuff reading in effect at that time. It is worked out from the trend, so it adds nothing to the QR.
- **Name in the QR (team decision, 22 Nov).** It helps the hospital match the patient. The trade-off: under UU 27/2022 Pasal 4(2) health data is specific personal data, anyone who scans the label sees name and vitals together, and the URL stays in the phone's browser history. `--no-name` turns it off.
- **CRC32 check.** A misread or cut-off URL shows "pindai ulang" instead of wrong numbers.
- **Extensible format.** Optional data sits in tagged sections after the main block. Older viewers skip sections they don't know, and labels made without the newer sections still open.

## Trend step by transport length

Simulated deteriorating patient with name and per-minute PPG BP:

| Transport | Default (max version 15) | `--max-version 12` |
|---|---|---|
| 15 min | 1 min, 15 points, v11 | 1 min, 15 points, v11 |
| 30 min | 1 min, 30 points, v13 | 2 min, 15 points, v11 |
| 45 min | 1 min, 45 points, v14 | 2 min, 23 points, v12 |
| 60 min | 1 min, 60 points, v15 | 3 min, 21 points, v12 |
| 90 min | 2 min, 45 points, v14 | 4 min, 23 points, v12 |
| 120 min | 2 min, 60 points, v15 | 7 min, 18 points, v12 |
| 180 min | 3 min, 60 points, v15 | 8 min, 23 points, v12 |
| 240 min | 4 min, 60 points, v14 | 9 min, 28 points, v12 |

The terminal prints the step it chose every time you make a label.

## QR size with the example records (default settings)

| Record | Trend | QR version | Module size |
|---|---|---|---|
| Deffandio, 30 min | 30 × 1 min | 13 | 0.50 mm |
| Rina, 40 min | 40 × 1 min | 13 | 0.50 mm |
| Rina, 150 min | 51 × 3 min | 14 | 0.50 mm |
| Deffandio with `--max-version 12` | 16 × 2 min | 12 | 0.63 mm |

## Testing on real phones (before the demo)

- [ ] Print a label. Scan it with at least 3 phones (one older Android, one iPhone) at 10 to 30 cm using the built-in camera.
- [ ] Check the page matches the paper: category, NEWS2, last vitals, cuff BP.
- [ ] Scan once with internet, switch to aeroplane mode, scan again. The page should still open.
- [ ] Crease or partly cover the label. You should get the "pindai ulang" message or a correct page, never wrong numbers.
- [ ] Try the WhatsApp and Google Lens scanners too; some in-app browsers are old.

## Limitations and future work

- **Anyone can make a URL.** The CRC catches scan errors, not forgery. A digital signature (Ed25519, 64 bytes) with the public key in the page would prove a label came from a SIREN console.
- **Anyone who scans the label can read it.** Encrypting the payload would need a key the hospital holds; out of scope for the capstone.
- **Browser support.** The page needs `DecompressionStream("deflate-raw")`: Chrome or Android WebView 103+, Safari 16.4+ (iOS 16.4), Firefox 113+. Older browsers get a clear message.
- **Snapshot, not monitoring.** The page shows when the data ends and does not update.
