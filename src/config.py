"""Load environment configuration for the agent backend/ETL."""
import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class Settings:
    def __init__(self) -> None:
        self.pageindex_api_key = os.getenv("PAGEINDEX_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")

    def validate(self, require_openai: bool = True, require_pageindex: bool = True) -> None:
        """Raise if required keys are missing.

        Args:
            require_openai: enforce OPENAI_API_KEY presence.
            require_pageindex: enforce PAGEINDEX_API_KEY presence.
        """
        missing = []
        if require_pageindex and not self.pageindex_api_key:
            missing.append("PAGEINDEX_API_KEY")
        if require_openai and not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"Missing required environment variables: {names}")

settings = Settings()
