from functools import lru_cache

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telnyx_api_key: str = Field(default="", alias="TELNYX_API_KEY")
    telnyx_api_base_url: str = Field(default="https://api.telnyx.com/v2", alias="TELNYX_API_BASE_URL")
    telnyx_connection_id: str = Field(default="", alias="TELNYX_CONNECTION_ID")
    telnyx_from_number: str = Field(default="", alias="TELNYX_FROM_NUMBER")
    telnyx_ivr_assistant_id: str = Field(default="", alias="TELNYX_IVR_ASSISTANT_ID")
    telnyx_representative_assistant_id: str = Field(default="", alias="TELNYX_REPRESENTATIVE_ASSISTANT_ID")
    telnyx_public_key: str = Field(default="", alias="TELNYX_PUBLIC_KEY")

    public_base_url: str = Field(default="", alias="PUBLIC_BASE_URL")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    start_transcription_during_ivr: bool = Field(default=True, alias="START_TRANSCRIPTION_DURING_IVR")
    transcription_engine: str = Field(default="Deepgram", alias="TRANSCRIPTION_ENGINE")
    transcription_model: str = Field(default="deepgram/nova-3", alias="TRANSCRIPTION_MODEL")
    transcription_language: str = Field(default="en", alias="TRANSCRIPTION_LANGUAGE")
    transcription_tracks: str = Field(default="both", alias="TRANSCRIPTION_TRACKS")

    hold_confidence_threshold: float = Field(default=0.72, alias="HOLD_CONFIDENCE_THRESHOLD")
    representative_confidence_threshold: float = Field(default=0.68, alias="REPRESENTATIVE_CONFIDENCE_THRESHOLD")
    max_hold_seconds: int = Field(default=1800, alias="MAX_HOLD_SECONDS")

    def required_missing(self) -> list[str]:
        required = {
            "TELNYX_API_KEY": self.telnyx_api_key,
            "TELNYX_CONNECTION_ID": self.telnyx_connection_id,
            "TELNYX_FROM_NUMBER": self.telnyx_from_number,
            "TELNYX_IVR_ASSISTANT_ID": self.telnyx_ivr_assistant_id,
            "TELNYX_REPRESENTATIVE_ASSISTANT_ID": self.telnyx_representative_assistant_id,
            "PUBLIC_BASE_URL": self.public_base_url,
        }
        return [name for name, value in required.items() if not value]

    @property
    def webhook_url(self) -> str:
        return f"{self.public_base_url.rstrip('/')}/webhooks/telnyx"


@lru_cache
def get_settings() -> Settings:
    return Settings()
