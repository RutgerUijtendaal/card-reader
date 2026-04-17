from pathlib import Path
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CARD_READER_", env_file=".env", extra="ignore")

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    database_path: Path = Path("card_reader.db")
    app_data_dir: Path = Path(
        os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    ) / "card-reader"
    low_confidence_threshold: float = 0.8

    @property
    def image_store_dir(self) -> Path:
        return self.app_data_dir / "images"


settings = Settings()
