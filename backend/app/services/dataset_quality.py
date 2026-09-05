from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import ROOT, settings
from app.schemas import DatasetQuality, EvaluationMetricSet, ModelQuality
from app.services.class_names import class_list, names_from_model, normalize_class_name

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def model_display_name(inference) -> str:
    if inference is not None and getattr(inference, "weights", None):
        return Path(inference.weights).name
    return Path(settings.model_path).name


def model_task(inference) -> str:
    model = getattr(inference, "model", None) if inference is not None else None
    if model is not None:
        return str(getattr(model, "task", "detect") or "detect")
    return "detect"


def live_class_names(inference) -> dict[int, str]:
    if inference is None:
        return {}
    return names_from_model(getattr(inference, "names", None))


def onnx_available(model_path: Path | None = None) -> bool:
    path = Path(model_path or settings.model_path)
    if path.with_suffix(".onnx").is_file():
        return True
    parent = path.parent if path.suffix else path
    if parent.is_dir() and any(parent.glob("*.onnx")):
        return True
    root_onnx = ROOT / "best.onnx"
    return root_onnx.is_file()


def empty_metrics() -> EvaluationMetricSet:
    return EvaluationMetricSet(
        precision=0.0,
        recall=0.0,
        mAP50=0.0,
        mAP50_95=0.0,
        inference_ms_cpu=0.0,
        confidence_threshold=settings.default_conf_threshold,
        test_images=0,
        test_annotations=0,
    )


def _label_path_for_image(image_path: Path) -> Path | None:
    same_dir = image_path.with_suffix(".txt")
    if same_dir.is_file():
        return same_dir
    parts = list(image_path.parts)
    if "images" in parts:
        swapped = ["labels" if part == "images" else part for part in parts]
        candidate = Path(swapped[0]).joinpath(*swapped[1:]).with_suffix(".txt")
        if candidate.is_file():
            return candidate
    return None


def _parse_yolo_label(label_path: Path) -> tuple[list[tuple[int, float, float, float, float]], int]:
    annotations: list[tuple[int, float, float, float, float]] = []
    issues = 0
    text = label_path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return annotations, issues
    for raw in text.splitlines():
        parts = raw.strip().split()
        if len(parts) != 5:
            issues += 1
            continue
        try:
            cls = int(float(parts[0]))
            cx, cy, bw, bh = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
        except ValueError:
            issues += 1
            continue
        if cls < 0:
            issues += 1
            continue
        if not all(0.0 <= value <= 1.0 for value in (cx, cy, bw, bh)):
            issues += 1
        annotations.append((cls, cx, cy, bw, bh))
    return annotations, issues


def scan_dataset(dataset_dir: Path, names: dict[int, str] | None = None) -> DatasetQuality | None:
    if not dataset_dir.is_dir():
        return None

    images = [
        path
        for path in dataset_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not images:
        return None

    labeled = 0
    background = 0
    total_annotations = 0
    class_counts: dict[str, int] = {}
    sizes: set[str] = set()
    issues = 0

    for image_path in images:
        label_path = _label_path_for_image(image_path)
        if label_path is None:
            background += 1
            continue
        annotations, label_issues = _parse_yolo_label(label_path)
        issues += label_issues
        if not annotations:
            background += 1
            continue
        labeled += 1
        total_annotations += len(annotations)
        for cls, *_ in annotations:
            label = (names or {}).get(cls) or normalize_class_name(f"class_{cls}", cls)
            class_counts[label] = class_counts.get(label, 0) + 1

    coverage = (labeled / len(images) * 100.0) if images else 0.0
    summary = (
        f"Live scan of {dataset_dir.name}: {labeled} labeled / {len(images)} images "
        f"({coverage:.1f}% labeled)."
    )
    return DatasetQuality(
        total_images=len(images),
        labeled_images=labeled,
        background_images=background,
        total_annotations=total_annotations,
        class_counts=class_counts,
        image_sizes=sorted(sizes),
        label_issues=issues,
        summary=summary,
    )


def unresolved_dataset() -> DatasetQuality:
    return DatasetQuality(
        total_images=0,
        labeled_images=0,
        background_images=0,
        total_annotations=0,
        class_counts={},
        image_sizes=[],
        label_issues=0,
        summary="No dataset folder is configured, so counts are unknown for this model.",
    )


def _snapshot_paths(model_path: Path) -> list[Path]:
    configured = getattr(settings, "quality_snapshot_path", None)
    paths = []
    if configured:
        paths.append(Path(configured))
    paths.extend(
        [
            model_path.parent / "quality.json",
            model_path.with_suffix(".quality.json"),
            ROOT / "ml" / "data" / "model_quality.json",
        ]
    )
    return paths


def _metrics_from_dict(payload: dict[str, Any]) -> EvaluationMetricSet:
    return EvaluationMetricSet(
        precision=float(payload.get("precision", 0.0)),
        recall=float(payload.get("recall", 0.0)),
        mAP50=float(payload.get("mAP50", 0.0)),
        mAP50_95=float(payload.get("mAP50_95", 0.0)),
        inference_ms_cpu=float(payload.get("inference_ms_cpu", 0.0)),
        confidence_threshold=float(payload.get("confidence_threshold", settings.default_conf_threshold)),
        test_images=int(payload.get("test_images", 0)),
        test_annotations=int(payload.get("test_annotations", 0)),
    )


def _snapshot_matches(payload: dict[str, Any], model_path: Path) -> bool:
    suffix = str(payload.get("model_path_suffix") or "").replace("\\", "/").strip()
    if suffix and suffix in str(model_path).replace("\\", "/"):
        return True
    name = str(payload.get("model_name") or payload.get("weights_name") or "").strip()
    if name:
        return Path(name).name == model_path.name
    return True


def load_quality_snapshot(model_path: Path) -> dict[str, Any] | None:
    for path in _snapshot_paths(model_path):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict) and _snapshot_matches(payload, model_path):
            payload["_source_path"] = str(path)
            return payload
    return None


def build_model_quality(inference) -> ModelQuality:
    names = live_class_names(inference)
    classes = class_list(names)
    task = model_task(inference)
    model_path = Path(getattr(inference, "weights", None) or settings.model_path)
    snapshot = load_quality_snapshot(model_path)
    dataset_dir = Path(settings.dataset_dir) if settings.dataset_dir else None
    if dataset_dir is None:
        fallback = ROOT / "Dataset"
        dataset_dir = fallback if fallback.is_dir() else None
    scanned = scan_dataset(dataset_dir, names) if dataset_dir else None

    if snapshot:
        dataset_payload = snapshot.get("dataset") or {}
        dataset = scanned or DatasetQuality(
            total_images=int(dataset_payload.get("total_images", 0)),
            labeled_images=int(dataset_payload.get("labeled_images", 0)),
            background_images=int(dataset_payload.get("background_images", 0)),
            total_annotations=int(dataset_payload.get("total_annotations", 0)),
            class_counts=dataset_payload.get("class_counts") or {},
            image_sizes=list(dataset_payload.get("image_sizes") or []),
            label_issues=int(dataset_payload.get("label_issues", 0)),
            summary=str(dataset_payload.get("summary") or "Loaded from a model quality snapshot."),
        )
        snapshot_classes = snapshot.get("classes")
        if snapshot_classes and not classes:
            classes = [normalize_class_name(item) for item in snapshot_classes]
        limitations = list(snapshot.get("limitations") or [])
        next_improvements = list(snapshot.get("next_improvements") or [])
        evaluation_split = str(snapshot.get("evaluation_split") or "quality snapshot")
        primary = _metrics_from_dict(snapshot.get("primary_metrics") or {})
        sweep = _metrics_from_dict(snapshot.get("pr_sweep_metrics") or snapshot.get("primary_metrics") or {})
        quality_available = True
        metrics_source = "snapshot"
    else:
        dataset = scanned or unresolved_dataset()
        limitations = [
            "No quality snapshot was found next to this checkpoint, so accuracy numbers are unavailable.",
            "Class names come from the loaded model, not a fixed debris taxonomy.",
        ]
        next_improvements = [
            "Run validation on this model's dataset and save quality.json beside the weights.",
            "Point DATASET_DIR at a YOLO image/label tree to show live dataset counts.",
        ]
        evaluation_split = "not evaluated"
        primary = empty_metrics()
        sweep = empty_metrics()
        quality_available = False
        metrics_source = "none"

    if not classes:
        classes = sorted(dataset.class_counts.keys())

    return ModelQuality(
        model_name=model_display_name(inference),
        task=task,
        classes=classes,
        segmentation_support=(task == "segment"),
        onnx_available=onnx_available(model_path),
        evaluation_split=evaluation_split,
        quality_available=quality_available,
        metrics_source=metrics_source,
        primary_metrics=primary,
        pr_sweep_metrics=sweep,
        dataset=dataset,
        limitations=limitations,
        next_improvements=next_improvements,
    )
