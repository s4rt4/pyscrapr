"""Application configuration — loaded from environment / .env file."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # scraper_app/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Paths
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    download_dir: Path = BASE_DIR / "downloads"
    log_dir: Path = BASE_DIR / "logs"

    # Database
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'scraper.db'}"

    # Scraping
    max_concurrent_downloads: int = 8
    default_timeout: int = 15
    default_user_agent: str = "PyScrapr/1.0 (+https://github.com/local)"

    # Filter defaults
    min_image_bytes: int = 5 * 1024
    min_image_width: int = 100
    min_image_height: int = 100

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Logging
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

# Ensure dirs exist (cross-platform)
for path in (settings.data_dir, settings.download_dir, settings.log_dir):
    path.mkdir(parents=True, exist_ok=True)
