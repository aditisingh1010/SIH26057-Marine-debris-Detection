from pathlib import Path

from app.core.config import discover_model_path


def test_discover_model_path_stays_inside_project(tmp_path: Path):
    weights = tmp_path / "ml" / "data" / "exp_runs" / "run_a" / "weights"
    weights.mkdir(parents=True)
    (weights / "best.pt").write_bytes(b"fake")

    found = discover_model_path(tmp_path)
    assert found == weights / "best.pt"
    assert found.is_relative_to(tmp_path)


def test_discover_prefers_root_best_pt(tmp_path: Path):
    (tmp_path / "best.pt").write_bytes(b"root")
    nested = tmp_path / "ml" / "data" / "exp_runs" / "run_a" / "weights"
    nested.mkdir(parents=True)
    (nested / "best.pt").write_bytes(b"nested")

    found = discover_model_path(tmp_path)
    assert found == tmp_path / "best.pt"
