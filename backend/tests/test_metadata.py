import pytest
from app.services.metadata import parse_metadata_text


def test_json_lat_lon():
    meta = parse_metadata_text('{"latitude": 15.1, "longitude": 73.2}', "nav.json")
    assert meta["latitude"] == 15.1
    assert meta["longitude"] == 73.2
    assert meta.get("pixel_size_m") is None


def test_csv_aliases():
    text = "lat,lon,pixel_size_m\n12.5,77.0,0.5\n"
    meta = parse_metadata_text(text, "nav.csv")
    assert meta["latitude"] == 12.5
    assert meta["longitude"] == 77.0
    assert meta["pixel_size_m"] == 0.5


def test_json_extra_aliases():
    meta = parse_metadata_text(
        '{"nav_lat": 8.1, "nav_lon": 77.5, "resolution_m": 0.2, "heading_deg": 45}',
        "nav.json",
    )
    assert meta["latitude"] == 8.1
    assert meta["longitude"] == 77.5
    assert meta["pixel_size_m"] == 0.2
    assert meta["heading"] == 45.0


def test_bad_json_raises():
    with pytest.raises(ValueError):
        parse_metadata_text("{not json", "nav.json")
