from __future__ import annotations


def normalize_class_name(name: object, class_id: int | None = None) -> str:
    """Turn a model label into a stable id without assuming a dataset taxonomy."""
    text = str(name or "").strip().lower().replace("-", "_").replace(" ", "_")
    text = "".join(ch for ch in text if ch.isalnum() or ch == "_")
    while "__" in text:
        text = text.replace("__", "_")
    text = text.strip("_")
    if text:
        return text
    if class_id is None:
        return "object"
    return f"class_{int(class_id)}"


def names_from_model(names: dict | list | None) -> dict[int, str]:
    if names is None:
        return {}
    if isinstance(names, dict):
        return {
            int(key): normalize_class_name(value, int(key))
            for key, value in names.items()
        }
    return {
        index: normalize_class_name(value, index)
        for index, value in enumerate(names)
    }


def class_list(names: dict[int, str] | None) -> list[str]:
    if not names:
        return []
    return list(dict.fromkeys(names[key] for key in sorted(names)))
