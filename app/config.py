from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str
    data_dir: str = "/data"
    upload_dir: str = "/data/uploads"
    db_path: str = "/data/db/meetings.db"
    max_upload_size_mb: int = 25
    log_level: str = "INFO"

    # CORS — empty list means no origins allowed (deny all by default)
    cors_origins: List[str] = []

    # Google Workspace (gws) integration
    gws_enabled: bool = False
    gws_folder_id: Optional[str] = None  # Google Drive folder ID to save docs into


settings = Settings()
