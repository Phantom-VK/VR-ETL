"""Load environment configuration for the agent backend/ETL."""
import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class Settings:
    def __init__(self) -> None:
        self.pageindex_api_key = os.getenv("PAGEINDEX_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

    def validate(self) -> None:
        missing = []
        if not self.pageindex_api_key:
            missing.append("PAGEINDEX_API_KEY")
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"Missing required environment variables: {names}")

settings = Settings()
