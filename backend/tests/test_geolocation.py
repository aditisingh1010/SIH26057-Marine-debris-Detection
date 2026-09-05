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


def test_heading_90_degrees_rotates_east_offset_to_north():
    bbox = {"x": 90, "y": 45, "width": 10, "height": 10}
    meta0 = {"latitude": 15.0, "longitude": 73.0, "pixel_size_m": 1.0, "heading": 0.0}
    meta90 = {"latitude": 15.0, "longitude": 73.0, "pixel_size_m": 1.0, "heading": 90.0}
    a = geolocate_box(bbox, 100, 100, meta0)
    b = geolocate_box(bbox, 100, 100, meta90)
    assert a["status"] == "computed"
    assert b["status"] == "computed"
    assert a["latitude"] == 15.0
    assert a["longitude"] != 73.0
    assert b["longitude"] == 73.0
    assert b["latitude"] != 15.0


def test_box_size_meters():
    from app.services.geolocation import box_size_meters

    w, h = box_size_meters({"x": 0, "y": 0, "width": 20, "height": 10}, 0.5)
    assert w == 10.0
    assert h == 5.0
    assert box_size_meters({"width": 10, "height": 10}, None) == (None, None)


def test_polar_longitude_does_not_explode():
    geo = geolocate_box(
        {"x": 90, "y": 40, "width": 10, "height": 10},
        100,
        100,
        {"latitude": 90.0, "longitude": 0.0, "pixel_size_m": 1.0, "heading": 0.0},
    )
    assert geo["status"] == "computed"
    assert geo["longitude"] == 0.0
