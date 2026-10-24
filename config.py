from pathlib import Path
from dotenv import load_dotenv  
import os

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Helper function to streamline environment variable retrieval and validation
def _require_env(name: str) -> str:
    """Return a non-empty environment variable or fail with a clear message."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set; check your .env file")
    return value

CONTACT_EMAIL = _require_env("AUCTION_RESEARCH_CONTACT")
BASE_URL = _require_env("BASE_URL")
PROJECT_ROOT = Path(__file__).resolve().parent

# Becomes the user agent header for all API requests
PROJECT_USER_AGENT = (
    "MAC.BIDAuctionResearch/0.1 "
    "(BYU-Idaho senior project: bid-prediction research; "
    f"contact: {CONTACT_EMAIL})"
)
