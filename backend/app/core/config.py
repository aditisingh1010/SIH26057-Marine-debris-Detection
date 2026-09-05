from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


def discover_model_path(root: Path) -> Path:
    """Find weights relative to the project, never a user home path."""
    named = [
        root / "best.pt",
        root / "ml" / "weights" / "best.pt",
        root / "backend" / "best.pt",
    ]
    for candidate in named:
        if candidate.is_file():
            return candidate

    runs_root = root / "ml" / "data" / "exp_runs"
    if runs_root.is_dir():
        found = sorted(
            runs_root.glob("*/weights/best.pt"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if found:
            return found[0]
    return named[0]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        extra="ignore",
        protected_namespaces=(),
    )

    service_name: str = "aquax-api"
    model_path: Path = discover_model_path(ROOT)
    storage_dir: Path = ROOT / "storage"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
    max_upload_mb: int = 80
    allowed_suffixes: str = ".png,.jpg,.jpeg,.tif,.tiff"
    default_conf_threshold: float = 0.25
    dataset_dir: Path | None = None
    quality_snapshot_path: Path | None = None

settings = Settings()
if not settings.model_path.is_absolute():
    settings.model_path = (ROOT / settings.model_path).resolve()
if not settings.storage_dir.is_absolute():
    settings.storage_dir = (ROOT / settings.storage_dir).resolve()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
