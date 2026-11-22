"""Writes the example records used by the tests and the README.

    python examples/make_example.py

Readings come every 10 s, as the console snapshots them. Each reading carries
a PPG blood-pressure estimate (sbp_ppg, dbp_ppg) from the calibrated trend
model; it is empty before the first cuff and while the finger is off.
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


def interp(points, m):
    """Linear interpolation through (minute, value) pairs, flat outside."""
    if m <= points[0][0]:
        return points[0][1]
    for (m0, v0), (m1, v1) in zip(points, points[1:]):
        if m <= m1:
            return v0 + (v1 - v0) * (m - m0) / (m1 - m0)
    return points[-1][1]


def simulate(t0, minutes, cuffs, vitals, acvpu_at, on_o2_at, dropouts, seed):
    """vitals(m, rng) -> (hr, spo2, rr, temp). cuffs = [(minute, sys, dia)]."""
    rng = random.Random(seed)
    true_sys = [(m, s) for m, s, _ in cuffs]
    true_dia = [(m, d) for m, _, d in cuffs]
    readings, worst = [], "HIJAU"
    for k in range(minutes * 6):
        m = k / 6
        hr, spo2, rr, temp = vitals(m, rng)
        on_o2 = on_o2_at is not None and m >= on_o2_at
        acvpu = acvpu_at(m)
        sbp_cuff = [c[1] for c in cuffs if c[0] <= m][-1]
        finger_off = any(a <= k < b for a, b in dropouts)
        calibrated = m >= cuffs[0][0]
        sbp_ppg = interp(true_sys, m) + rng.gauss(0, 3) if calibrated and not finger_off else None
        dbp_ppg = interp(true_dia, m) + rng.gauss(0, 2) if calibrated and not finger_off else None
        score = news2(hr, spo2, rr, temp, sbp_cuff, on_o2, acvpu)   # NEWS2 uses the cuff, never PPG
        readings.append({
            "t": (t0 + timedelta(seconds=10 * k)).isoformat(),
            "hr": None if finger_off else round(hr, 1),
            "spo2": None if finger_off else round(min(100, spo2), 1),
            "rr": round(rr, 1), "temp": round(temp, 2),
            "sbp_ppg": None if sbp_ppg is None else round(sbp_ppg),
            "dbp_ppg": None if dbp_ppg is None else round(dbp_ppg),
            "news2": score, "colour": colour(score),
        })
        worst = max(worst, colour(score), key=["HIJAU", "KUNING", "MERAH"].index)
    return readings, worst


def deteriorating(minutes=40, seed=7):
    """Bleeding after a motorbike fall: slowly worsening shock."""
    t0 = datetime(2026, 11, 20, 9, 2, tzinfo=WIB)
    cuffs = [(0, 124, 78), (5, 116, 74), (15, 104, 68), (25, 96, 62), (33, 88, 56)]
    if minutes > 40:
        cuffs += [(m, max(70, 88 - (m - 33) // 4), max(45, 56 - (m - 33) // 6)) for m in range(45, minutes, 12)]

    def vitals(m, rng):
        f = min(1, m / minutes)
        return (92 + 34 * f + 3 * math.sin(m * 6 / 9) + rng.gauss(0, 1.5),
                96 - 4 * f + (2 if m >= 20 else 0) + rng.gauss(0, 0.6),
                18 + 7 * f + rng.gauss(0, 0.8),
                36.6 - 0.5 * f + rng.gauss(0, 0.04))

    rng = random.Random(seed + 1)
    dropouts = [(k, k + 2) for k in range(minutes * 6) if rng.random() < 0.015]
    readings, worst = simulate(t0, minutes, cuffs, vitals, lambda m: "alert" if m < 30 else "confusion",
                               20, dropouts, seed)
    last = readings[-1]
    return {
        "code": "SRN-261120-004", "name": "Rina Marlina", "age": 67, "sex": "P",
        "complaint": "Jatuh dari motor, nyeri paha kanan", "unit": "SIREN-01",
        "acvpu": "confusion", "on_oxygen": True, "pain": 7, "start_colour": "KUNING",
        "colour": last["colour"], "worst_colour": worst, "news2": last["news2"], "news2_measured": 7,
        "alerts": ["shock_index", "sbp_low", "new_confusion", "news2_rise", "bp_trend"],
        "simulated": True,
        "printed_at": (t0 + timedelta(minutes=minutes, seconds=20)).isoformat(),
        "cuffs": [{"t": (t0 + timedelta(minutes=m)).isoformat(), "sys": s, "dia": d} for m, s, d in cuffs],
        "readings": readings,
    }


def deffandio(minutes=30, seed=22):
    """Smoke inhalation at a building fire: improves on oxygen from minute 3."""
    t0 = datetime(2026, 11, 22, 14, 5, tzinfo=WIB)
    cuffs = [(0, 138, 86), (5, 132, 84), (15, 126, 80), (27, 122, 78)]

    def vitals(m, rng):
        rec = 1 - math.exp(-max(0, m - 3) / 8)
        return (124 - 30 * rec + 2 * math.sin(m * 6 / 7) + rng.gauss(0, 1.5),
                89 + 8 * rec + rng.gauss(0, 0.6),
                28 - 9 * rec + rng.gauss(0, 0.8),
                37.2 + rng.gauss(0, 0.04))

    readings, worst = simulate(t0, minutes, cuffs, vitals, lambda m: "alert", 3, [(60, 64)], seed)
    last = readings[-1]
    return {
        "code": "SRN-261122-011", "name": "Deffandio", "age": 22, "sex": "L",
        "complaint": "Sesak napas, terhirup asap kebakaran gedung", "unit": "SIREN-02",
        "acvpu": "alert", "on_oxygen": True, "pain": 3, "start_colour": "MERAH",
        "colour": last["colour"], "worst_colour": worst, "news2": last["news2"], "news2_measured": 7,
        "alerts": ["spo2_low", "rr_high"], "simulated": True,
        "printed_at": (t0 + timedelta(minutes=minutes, seconds=15)).isoformat(),
        "cuffs": [{"t": (t0 + timedelta(minutes=m)).isoformat(), "sys": s, "dia": d} for m, s, d in cuffs],
        "readings": readings,
    }


def write(name, record):
    (HERE / name).write_text(json.dumps(record, indent=1), encoding="utf-8")


if __name__ == "__main__":
    write("patient_deteriorating.json", deteriorating())
    write("patient_long_transport.json", deteriorating(minutes=150, seed=3))
    write("patient_deffandio.json", deffandio())
    print("written 3 example records")
