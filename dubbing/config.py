from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    target_language_code: str = Field("pl")

    output_dir: Path = Field(
        default=Path("dubbed_output")
    )
    input_video: Path = Field(
        default=Path("input.mp4")
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def target_language_name(self) -> str:
        mapping = {
            "pl": "Polish",
            "ua": "Ukrainian",
            "de": "German",
            "es": "Spanish",
            "ru": "Russian",
        }
        return mapping.get(self.target_language_code.lower(), self.target_language_code.capitalize())

    @property
    def output_video(self) -> Path:
        return Path(f"output_dubbed_{self.target_language_code}.mp4")


settings = Settings()
