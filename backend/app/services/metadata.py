import csv
import io
import json

LAT_ALIASES = ("lat", "latitude")
LON_ALIASES = ("lon", "lng", "long", "longitude")
HEAD_ALIASES = ("heading", "course", "yaw")
PIX_ALIASES = ("pixel_size_m", "pixel_size", "gsd")

_EMPTY = {
    "latitude": None,
    "longitude": None,
    "heading": None,
    "pixel_size_m": None,
}


def parse_metadata_text(text, filename):
    """Parse optional JSON/CSV navigation metadata. Never invents values."""
    if text is None or not str(text).strip():
        return dict(_EMPTY)

    name = (filename or "").lower()
    if name.endswith(".json"):
        raw = _parse_json(text)
    else:
        raw = _parse_csv(text)
    return _extract_fields(raw)


def _parse_json(text):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON metadata") from exc

    if isinstance(data, list):
        if not data:
            raise ValueError("JSON array has no objects")
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError("JSON metadata must be an object or array of objects")
    return data


def _parse_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    try:
        row = next(reader)
    except StopIteration as exc:
        raise ValueError("CSV metadata has no data row") from exc
    return row


def _extract_fields(mapping):
    lower = {}
    for key, value in mapping.items():
        if key is None:
            continue
        lower[str(key).strip().lower()] = value
    return {
        "latitude": _first_number(lower, LAT_ALIASES),
        "longitude": _first_number(lower, LON_ALIASES),
        "heading": _first_number(lower, HEAD_ALIASES),
        "pixel_size_m": _first_number(lower, PIX_ALIASES),
    }


def _first_number(mapping, aliases):
    for alias in aliases:
        if alias in mapping:
            return _to_float(mapping[alias])
    return None


def _to_float(value):
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, bool):
        raise ValueError("Invalid numeric metadata value")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid numeric metadata value") from exc
