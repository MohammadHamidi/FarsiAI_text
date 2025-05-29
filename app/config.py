import os
from pathlib import Path
from pydantic import BaseSettings, validator # Keep Pydantic if used for other settings
import logging
from typing import Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

class Settings(BaseSettings):
    """Application settings with validation using Pydantic"""

    # Directory for output files
    BASE_DIR = Path(__file__).parent.parent  # points to /app
    OUT_DIR = os.getenv("OUT_DIR", str(BASE_DIR / "outputs"))

    # Allowed output formats - ONLY DOCX NOW
    ALLOWED_FORMATS: Set[str] = {"docx"} # MODIFIED

    # Maximum file age in hours before cleanup
    MAX_FILE_AGE_HOURS: int = int(os.getenv("MAX_FILE_AGE_HOURS", "24"))

    # Rate limiting: max requests per minute per IP
    RATE_LIMIT: int = int(os.getenv("RATE_LIMIT", "30"))

    # Maximum size of markdown input in bytes (1MB default)
    MAX_INPUT_SIZE: int = int(os.getenv("MAX_INPUT_SIZE", "1048576"))

    # Enable debug mode
    DEBUG: bool = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")

    # Firebase Analytics
    FIREBASE_SERVICE_ACCOUNT_KEY_PATH: str | None = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
    FIREBASE_ANALYTICS_ENABLED: bool = os.getenv("FIREBASE_ANALYTICS_ENABLED", "false").lower() in ("true", "1", "yes")

    # Google Analytics 4 Measurement Protocol
    GA_MEASUREMENT_ID: str | None = os.getenv("GA_MEASUREMENT_ID")
    GA_API_SECRET: str | None = os.getenv("GA_API_SECRET")

    @validator("OUT_DIR")
    def create_out_dir(cls, v):
        """Ensure output directory exists"""
        os.makedirs(v, exist_ok=True)
        return v

    class Config:
        env_file = ".env" # If you use a .env file
        case_sensitive = True

# Create settings instance
settings = Settings()

# Export settings as module variables for backward compatibility (if needed elsewhere)
BASE = Path(__file__).parent.parent  # that's /app
OUT_DIR = os.getenv("OUT_DIR", str(BASE / "outputs"))
ALLOWED = settings.ALLOWED_FORMATS # This will now be {"docx"}
MAX_FILE_AGE_HOURS = settings.MAX_FILE_AGE_HOURS
RATE_LIMIT = settings.RATE_LIMIT
MAX_INPUT_SIZE = settings.MAX_INPUT_SIZE
DEBUG = settings.DEBUG

# Firebase Settings
FIREBASE_SERVICE_ACCOUNT_KEY_PATH = settings.FIREBASE_SERVICE_ACCOUNT_KEY_PATH
FIREBASE_ANALYTICS_ENABLED = settings.FIREBASE_ANALYTICS_ENABLED

# Google Analytics Settings
GA_MEASUREMENT_ID = settings.GA_MEASUREMENT_ID
GA_API_SECRET = settings.GA_API_SECRET

# Set log level based on debug setting
if DEBUG:
    logging.getLogger().setLevel(logging.DEBUG)
else:
    logging.getLogger().setLevel(logging.INFO) # Ensure INFO for non-debug