"""Load environment configuration for the agent backend/ETL."""
import os
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class Settings:
    def __init__(self) -> None:
        self.pageindex_api_key = os.getenv("PAGEINDEX_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.api_key = os.getenv("API_KEY", "")
        self.base_url = os.getenv("BASE_URL", "")
        self.chat_model = os.getenv("CHAT_MODEL", "")
        self.reasoning_model = os.getenv("REASONING_MODEL", "")
        self.chat_temperature = float(os.getenv("CHAT_TEMPERATURE", "0.0"))
        self.reasoning_temperature = float(os.getenv("REASONING_TEMPERATURE", "0.0"))

    def validate(
        self,
        require_openai: bool = False,
        require_pageindex: bool = True,
        require_generic_llm: bool = False,
    ) -> None:
        """Raise if required keys are missing.

        Args:
            require_openai: enforce OPENAI_API_KEY presence.
            require_pageindex: enforce PAGEINDEX_API_KEY presence.
            require_generic_llm: enforce API_KEY/BASE_URL/MODEL_NAME presence.
        """
        missing = []
        if require_pageindex and not self.pageindex_api_key:
            missing.append("PAGEINDEX_API_KEY")
        if require_openai and not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if require_generic_llm:
            if not self.api_key:
                missing.append("API_KEY")
            if not self.base_url:
                missing.append("BASE_URL")
            if not self.model_name:
                missing.append("MODEL_NAME")
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"Missing required environment variables: {names}")

settings = Settings()
