from math import cos, radians, sin


def geolocate_box(bbox, image_width, image_height, metadata):
    """Map a detection box to WGS84 using survey metadata. Never invent GPS."""
    if not metadata:
        return {"latitude": None, "longitude": None, "status": "unavailable"}

    lat = metadata.get("latitude")
    lon = metadata.get("longitude")
    if lat is None or lon is None:
        return {"latitude": None, "longitude": None, "status": "unavailable"}

    pixel_size_m = metadata.get("pixel_size_m")
    if pixel_size_m is None:
        return {
            "latitude": lat,
            "longitude": lon,
            "status": "survey_position_only",
        }

    heading = metadata.get("heading") or 0.0
    cx = bbox["x"] + bbox["width"] / 2
    cy = bbox["y"] + bbox["height"] / 2
    dx_m = (cx - image_width / 2) * pixel_size_m
    dy_m = (image_height / 2 - cy) * pixel_size_m

    east = dx_m * cos(heading) - dy_m * sin(heading)
    north = dx_m * sin(heading) + dy_m * cos(heading)
    dlat = north / 111320
    dlon = east / (111320 * cos(radians(lat)))

    return {
        "latitude": round(lat + dlat, 7),
        "longitude": round(lon + dlon, 7),
        "status": "computed",
    }
