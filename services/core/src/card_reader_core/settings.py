from pathlib import Path
import os
import sys

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# services/core/src/settings.py -> parents[4] is repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8888",
    "http://127.0.0.1:8888",
    "tauri://localhost",
    "http://tauri.localhost",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CARD_READER_", env_file=".env", extra="ignore")

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: list[str] = DEFAULT_CORS_ORIGINS.copy()
    environment: str = os.getenv("CARD_READER_ENV", "development")
    database_path: Path = Path("card_reader.db")
    app_data_dir: Path | None = None
    low_confidence_threshold: float = 0.8
    save_debug_crops: bool = True

    @model_validator(mode="after")
    def _merge_default_cors_origins(self) -> "Settings":
        merged: list[str] = []
        for origin in [*DEFAULT_CORS_ORIGINS, *self.cors_origins]:
            compact = origin.strip()
            if compact and compact not in merged:
                merged.append(compact)
        self.cors_origins = merged
        return self

    @property
    def is_dev(self) -> bool:
        return self.environment.lower() in {"dev", "development", "local", "test"}

    @property
    def shared_app_data_dir(self) -> Path:
        if sys.platform.startswith("win"):
            base = Path(os.getenv("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
            return base / "Card Reader"
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "card-reader"
        return Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "card-reader"

    @property
    def storage_root_dir(self) -> Path:
        if self.app_data_dir is not None:
            return self.app_data_dir
        if self.is_dev:
            return REPO_ROOT / "storage"
        return self.shared_app_data_dir

    @property
    def image_store_dir(self) -> Path:
        return self.storage_root_dir / "images"

    @property
    def debug_crops_dir(self) -> Path:
        return self.storage_root_dir / "debug-crops"


settings = Settings()


