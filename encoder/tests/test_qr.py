import zxingcpp
from PIL import Image

from siren_qr import label, payload as P, qr

from .conftest import BASE


def test_url_shape(record):
    result = qr.make(record, BASE)
    base, digits = result.url.split("#")
    assert base == BASE and digits.isdigit()
    assert P.decode(digits)["code"] == record["code"]
    assert "Rina" not in result.url


def test_fits_label_budget(record, long_record):
    for rec in (record, long_record):
        result = qr.make(rec, BASE)
        assert result.version <= qr.MAX_VERSION


def test_tight_budget_widens_step(record):
    result = qr.make(record, BASE, max_version=8)
    assert result.version <= 8 and result.step_s > 60


def test_printed_label_scans_back_to_the_url(record):
    result = qr.make(record, BASE)
    image = label.render(record, result)
    assert image.width == label.WIDTH_PX
    found = zxingcpp.read_barcodes(image.convert("RGB"))
    assert [b.text for b in found if b.format == zxingcpp.BarcodeFormat.QRCode] == [result.url]


def test_label_scans_after_blur_and_downscale(record):
    """Rough stand-in for a phone photo of thermal paper."""
    from PIL import ImageFilter
    result = qr.make(record, BASE)
    image = label.render(record, result).convert("RGB")
    photo = image.resize((image.width * 3 // 4, image.height * 3 // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(0.8))
    assert any(b.text == result.url for b in zxingcpp.read_barcodes(photo))


def test_escpos_bytes(record):
    data = label.escpos_raster(label.render(record, qr.make(record, BASE)))
    assert data.startswith(b"\x1b\x40") and b"\x1d\x76\x30\x00" in data
