import statistics

import pytest

from siren_qr import payload as P


def test_round_trip_keeps_every_field(record):
    trend = P.bucket(record["readings"])
    out = P.decode(P.encode(record, trend))
    assert out["code"] == "SRN-261120-004"
    assert out["unit"] == "SIREN-01"
    assert out["complaint"] == record["complaint"]
    assert out["age"] == 67 and out["sex"] == "P" and out["acvpu"] == "C" and out["pain"] == 7
    assert out["on_oxygen"] and out["simulated"] and not out["handed_over"]
    assert out["colour"] == record["colour"] and out["start_colour"] == "KUNING"
    assert out["news2"] == record["news2"] and out["news2_measured"] == 7
    assert out["alerts"] == [a for a in P.ALERTS if a in record["alerts"]]
    assert [(c["sys"], c["dia"]) for c in out["cuffs"]] == [(c["sys"], c["dia"]) for c in record["cuffs"]]
    assert len(out["points"]) == len(trend.points) == 40
    assert out["step_s"] == 60


def test_points_are_median_vitals_and_worst_news2(record):
    trend = P.bucket(record["readings"])
    out = P.decode(P.encode(record, trend))
    minute0 = [r for r in record["readings"] if P._ts(r["t"]) < trend.start + 60]
    hrs = [r["hr"] for r in minute0 if r["hr"] is not None]
    assert out["points"][0]["hr"] == round(statistics.median(hrs))
    assert out["points"][0]["news2"] == max(r["news2"] for r in minute0)
    temps = [r["temp"] for r in minute0]
    assert abs(out["points"][0]["temp"] - statistics.median(temps)) <= 0.05 + 1e-9


def test_missing_values_survive():
    rec = {"code": "X", "readings": [
        {"t": 0, "hr": 80, "spo2": None, "rr": 16, "temp": None},
        {"t": 60, "hr": None, "spo2": 97, "rr": None, "temp": 36.6},
    ]}
    out = P.decode(P.encode(rec))
    assert out["points"][0]["spo2"] is None and out["points"][1]["hr"] is None
    assert out["points"][1]["temp"] == 36.6
    assert out["age"] is None and out["news2"] is None and out["colour"] is None


def test_empty_record_still_encodes():
    out = P.decode(P.encode({"code": "SRN-1", "printed_at": 1_000_000}))
    assert out["points"] == [] and out["code"] == "SRN-1"


def test_name_is_never_encoded(record):
    digits = P.encode(record)
    assert record["name"].encode() not in P.decompress(P.from_digits(digits))


def test_corruption_is_detected(record):
    raw = bytearray(P.pack(record, P.bucket(record["readings"])))
    raw[20] ^= 0x01
    with pytest.raises(P.PayloadError, match="checksum"):
        P.unpack(bytes(raw))


def test_unknown_alert_is_rejected(record):
    record["alerts"] = ["made_up"]
    with pytest.raises(P.PayloadError):
        P.encode(record)


def test_long_text_is_clipped_on_character_boundary():
    out = P.decode(P.encode({"code": "C", "complaint": "é" * 100}))
    assert out["complaint"] == "é" * 24


def test_step_widens_for_long_transports(long_record):
    trend = P.bucket(long_record["readings"])
    assert trend.step_s == 180 and len(trend.points) <= P.MAX_POINTS
