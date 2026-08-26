from app.services.geolocation import geolocate_box


def test_unavailable_without_lat_lon():
    geo = geolocate_box(
        bbox={"x": 10, "y": 10, "width": 8, "height": 8},
        image_width=100,
        image_height=100,
        metadata=None,
    )
    assert geo["status"] == "unavailable"
    assert geo["latitude"] is None
    assert geo["longitude"] is None


def test_survey_position_only_when_no_pixel_size():
    geo = geolocate_box(
        bbox={"x": 10, "y": 10, "width": 8, "height": 8},
        image_width=100,
        image_height=100,
        metadata={"latitude": 15.0, "longitude": 73.0},
    )
    assert geo["status"] == "survey_position_only"
    assert geo["latitude"] == 15.0
    assert geo["longitude"] == 73.0


def test_computed_differs_for_two_boxes():
    meta = {"latitude": 15.0, "longitude": 73.0, "pixel_size_m": 1.0, "heading": 0.0}
    a = geolocate_box({"x": 0, "y": 40, "width": 10, "height": 10}, 100, 100, meta)
    b = geolocate_box({"x": 90, "y": 40, "width": 10, "height": 10}, 100, 100, meta)
    assert a["status"] == "computed"
    assert b["status"] == "computed"
    assert a["longitude"] != b["longitude"]
