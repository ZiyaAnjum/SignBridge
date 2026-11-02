"""Core application configuration module."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """SignBridge ML Service Configuration."""
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Model & Inference
    DEVICE: str = "cpu"
    CONFIDENCE_THRESHOLD: float = 0.65
    EMERGENCY_WORDS: List[str] = ["emergency", "ambulance", "pain", "blood"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

