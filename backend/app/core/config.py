from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]
GHOST_POT_BASELINE = ROOT / "ml" / "data" / "exp_runs" / "ghost_pot_yolov8n_baseline" / "weights" / "best.pt"
ROOT_BASELINE = ROOT / "best.pt"

default_model_path = GHOST_POT_BASELINE if GHOST_POT_BASELINE.is_file() else ROOT_BASELINE

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        extra="ignore",
        protected_namespaces=(),
    )

    service_name: str = "aquax-api"
    model_path: Path = default_model_path
    storage_dir: Path = ROOT / "storage"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"
    max_upload_mb: int = 80
    allowed_suffixes: str = ".png,.jpg,.jpeg,.tif,.tiff"
    default_conf_threshold: float = 0.25

settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
