"""Load environment configuration for the agent backend/ETL."""
import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class Settings:
    def __init__(self) -> None:
        self.pageindex_api_key = os.getenv("PAGEINDEX_API_KEY", "")
        self.api_key = os.getenv("API_KEY", "")
        self.base_url = os.getenv("BASE_URL", "")
        self.chat_model = os.getenv("CHAT_MODEL", "")
        self.reasoning_model = os.getenv("REASONING_MODEL", "")

    def validate(
        self,
        require_pageindex: bool = True,
        require_generic_llm: bool = False,
    ) -> None:
        """Raise if required keys are missing.

        Args:
            require_pageindex: enforce PAGEINDEX_API_KEY presence.
            require_generic_llm: enforce API_KEY/BASE_URL/MODEL_NAME presence.
        """
        missing = []
        if require_pageindex and not self.pageindex_api_key:
            missing.append("PAGEINDEX_API_KEY")
        if require_generic_llm:
            if not self.api_key:
                missing.append("API_KEY")
            if not self.base_url:
                missing.append("BASE_URL")
            if not (self.chat_model or self.reasoning_model):
                missing.append("CHAT_MODEL/REASONING_MODEL")
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"Missing required environment variables: {names}")

settings = Settings()
