from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LM Studio / LLM settings
    lm_studio_url: str = Field(default="http://192.168.0.5:1234/v1")
    lm_studio_api_key: str = Field(default="lm-studio")
    llm_model: str = Field(default="")
    llm_temperature: float = Field(default=0.0)
    llm_max_output_tokens: int = Field(default=4096)
    llm_concurrency: int = Field(default=1)
    llm_timeout_s: float = Field(default=600.0)

    # Chunking
    chunk_max_chars: int = Field(default=8000)
    chunk_overlap_chars: int = Field(default=200)

    # Backend / Paths
    data_dir: Path = Field(default=Path("../data"))
    database_url: str = Field(default="sqlite:///../data/docextract.db")
    cors_origins: str = Field(default="http://localhost:3000")
    max_upload_mb: int = Field(default=50)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def resolved_data_dir(self) -> Path:
        base = Path(__file__).resolve().parent.parent
        if not self.data_dir.is_absolute():
            resolved = (base / self.data_dir).resolve()
        else:
            resolved = self.data_dir
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved


settings = Settings()
