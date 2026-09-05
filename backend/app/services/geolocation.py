from math import cos, radians, sin


def _center(bbox):
    x = float(bbox.get("x", bbox.get("x1", 0)))
    y = float(bbox.get("y", bbox.get("y1", 0)))
    width = float(bbox.get("width", 0))
    height = float(bbox.get("height", 0))
    if width <= 0 and "x2" in bbox:
        width = max(0.0, float(bbox["x2"]) - x)
    if height <= 0 and "y2" in bbox:
        height = max(0.0, float(bbox["y2"]) - y)
    return x, y, width, height, x + width / 2.0, y + height / 2.0


def box_size_meters(bbox, pixel_size_m):
    if pixel_size_m is None:
        return None, None
    size = float(pixel_size_m)
    if size <= 0:
        return None, None
    _x, _y, width, height, _cx, _cy = _center(bbox)
    return round(width * size, 3), round(height * size, 3)


def has_navigation_fix(metadata):
    if not metadata:
        return False
    lat = metadata.get("latitude", metadata.get("lat"))
    lon = metadata.get("longitude", metadata.get("lon"))
    return lat is not None and lon is not None


def geolocation_note(metadata):
    if not has_navigation_fix(metadata):
        return "Geolocation unavailable: no latitude/longitude in the attached metadata."
    if metadata.get("pixel_size_m") is None:
        return (
            "Survey position only: lat/lon were provided, but pixel size was not, "
            "so every detection shares the survey/towfish coordinate."
        )
    return (
        "Approximate object positions computed from survey lat/lon, heading, and pixel size. "
        "This is not full ping-by-ping sonar geometry."
    )


def geolocate_box(bbox, image_width, image_height, metadata):
    """Map a detection box to WGS84 using survey metadata. Never invent GPS."""
    if not has_navigation_fix(metadata):
        return {"latitude": None, "longitude": None, "status": "unavailable"}

    lat = float(metadata["latitude"] if metadata.get("latitude") is not None else metadata["lat"])
    lon = float(metadata["longitude"] if metadata.get("longitude") is not None else metadata["lon"])
    pixel_size_m = metadata.get("pixel_size_m")
    if pixel_size_m is None:
        return {
            "latitude": lat,
            "longitude": lon,
            "status": "survey_position_only",
        }

    heading = metadata.get("heading") or 0.0
    rad = radians(float(heading))
    _x, _y, _w, _h, cx, cy = _center(bbox)
    dx_m = (cx - image_width / 2.0) * float(pixel_size_m)
    dy_m = (image_height / 2.0 - cy) * float(pixel_size_m)

    east = dx_m * cos(rad) - dy_m * sin(rad)
    north = dx_m * sin(rad) + dy_m * cos(rad)
    dlat = north / 111320.0
    cos_lat = cos(radians(lat))
    dlon = 0.0 if abs(cos_lat) < 1e-6 else east / (111320.0 * cos_lat)

    return {
        "latitude": round(lat + dlat, 7),
        "longitude": round(lon + dlon, 7),
        "status": "computed",
    }
