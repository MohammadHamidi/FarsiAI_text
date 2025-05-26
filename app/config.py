import os
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
    OUT_DIR: str = os.getenv("OUT_DIR", "/tmp/outputs")

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
OUT_DIR = settings.OUT_DIR
ALLOWED = settings.ALLOWED_FORMATS # This will now be {"docx"}
MAX_FILE_AGE_HOURS = settings.MAX_FILE_AGE_HOURS
RATE_LIMIT = settings.RATE_LIMIT
MAX_INPUT_SIZE = settings.MAX_INPUT_SIZE
DEBUG = settings.DEBUG

# Set log level based on debug setting
if DEBUG:
    logging.getLogger().setLevel(logging.DEBUG)
else:
    logging.getLogger().setLevel(logging.INFO) # Ensure INFO for non-debug