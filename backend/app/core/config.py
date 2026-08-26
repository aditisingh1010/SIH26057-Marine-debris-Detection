from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        extra="ignore",
        protected_namespaces=(),
    )

    service_name: str = "aquax-api"
    model_path: Path = ROOT / "best.pt"
    storage_dir: Path = ROOT / "storage"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    max_upload_mb: int = 80
    allowed_suffixes: str = ".png,.jpg,.jpeg,.tif,.tiff"


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
