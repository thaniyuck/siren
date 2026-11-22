"""Writes the two example records used by the tests and the README.

A 40 min transport, readings every 10 s (as the console snapshots them),
with a patient who slowly deteriorates (bleeding after a motorbike fall).
"""

import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
WIB = timezone(timedelta(hours=7))


def news2(hr, spo2, rr, temp, sbp, on_o2, acvpu):
    s = 0
    s += 3 if rr <= 8 else 1 if rr <= 11 else 0 if rr <= 20 else 2 if rr <= 24 else 3
    s += 3 if spo2 <= 91 else 2 if spo2 <= 93 else 1 if spo2 <= 95 else 0
    s += 2 if on_o2 else 0
    s += 3 if hr <= 40 else 1 if hr <= 50 else 0 if hr <= 90 else 1 if hr <= 110 else 2 if hr <= 130 else 3
    s += 3 if temp <= 35 else 1 if temp <= 36 else 0 if temp <= 38 else 1 if temp <= 39 else 2
    s += 3 if sbp <= 90 else 2 if sbp <= 100 else 1 if sbp <= 110 else 0 if sbp <= 219 else 3
    s += 0 if acvpu == "alert" else 3
    return s


def colour(score):
    return "MERAH" if score >= 7 else "KUNING" if score >= 5 else "HIJAU"


def deteriorating(minutes=40, seed=7):
    rng = random.Random(seed)
    t0 = datetime(2026, 11, 20, 9, 2, tzinfo=WIB)
    cuffs = [(0, 124, 78), (5, 116, 74), (15, 104, 68), (25, 96, 62), (33, 88, 56)]
    readings, worst = [], "HIJAU"
    for k in range(minutes * 6):
        m = k / 6
        f = min(1, m / minutes)
        on_o2 = m >= 20
        hr = 92 + 34 * f + 3 * math.sin(k / 9) + rng.gauss(0, 1.5)
        spo2 = 96 - 4 * f + (2 if on_o2 else 0) + rng.gauss(0, 0.6)
        rr = 18 + 7 * f + rng.gauss(0, 0.8)
        temp = 36.6 - 0.5 * f + rng.gauss(0, 0.04)
        sbp = [c[1] for c in cuffs if c[0] <= m][-1]
        acvpu = "alert" if m < 30 else "confusion"
        if rng.random() < 0.03:                      # dropout: finger off the sensor
            hr_v, spo2_v = None, None
        else:
            hr_v, spo2_v = round(hr, 1), round(min(100, spo2), 1)
        score = news2(hr, spo2, rr, temp, sbp, on_o2, acvpu)
        readings.append({
            "t": (t0 + timedelta(seconds=10 * k)).isoformat(),
            "hr": hr_v, "spo2": spo2_v, "rr": round(rr, 1), "temp": round(temp, 2),
            "news2": score, "colour": colour(score),
        })
        worst = max(worst, colour(score), key=["HIJAU", "KUNING", "MERAH"].index)
    last = readings[-1]
    return {
        "code": "SRN-261120-004",
        "name": "Rina Marlina",
        "age": 67, "sex": "P",
        "complaint": "Jatuh dari motor, nyeri paha kanan",
        "unit": "SIREN-01",
        "acvpu": "confusion", "on_oxygen": True, "pain": 7,
        "start_colour": "KUNING",
        "colour": last["colour"], "worst_colour": worst,
        "news2": last["news2"], "news2_measured": 7,
        "alerts": ["shock_index", "sbp_low", "new_confusion", "news2_rise"],
        "simulated": True,
        "printed_at": (t0 + timedelta(minutes=minutes, seconds=20)).isoformat(),
        "cuffs": [{"t": (t0 + timedelta(minutes=m)).isoformat(), "sys": s, "dia": d} for m, s, d in cuffs],
        "readings": readings,
    }


if __name__ == "__main__":
    (HERE / "patient_deteriorating.json").write_text(json.dumps(deteriorating(), indent=1), encoding="utf-8")
    (HERE / "patient_long_transport.json").write_text(
        json.dumps(deteriorating(minutes=150, seed=3), indent=1), encoding="utf-8")
    print("written")
