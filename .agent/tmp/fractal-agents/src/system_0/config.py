from pydantic import BaseModel
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class AppSettings(BaseModel):
    # Redis settings
    ER_CACHE_BASE: str
    ER_CACHE_DB: str = "0"

    # API settings
    API_KEY: Optional[str] = None
    DEBUG_MODE: bool = False

    @property
    def er_cache_url(self) -> str:
        """
        Constructs a valid Redis URL from base and DB components.
        """
        base = self.ER_CACHE_BASE
        if base.endswith("/"):
            base = base[:-1]
        return f"{base}/{self.ER_CACHE_DB}"

    @classmethod
    def from_env(cls):
        """
        Creates settings from environment variables with validation.
        Will raise errors for missing required variables.
        """
        # Print all environment variables for debugging
        print("Environment variables:")
        for key, value in os.environ.items():
            print(f"  {key}: {value}")

        redis_base = os.environ.get("ER_CACHE_BASE")
        if not redis_base:
            # Fallback to a default value if missing
            print(
                "WARNING: ER_CACHE_BASE environment variable not found, using default"
            )
            redis_base = "redis://localhost:6379"

        redis_db = os.environ.get("ER_CACHE_DB", "0")

        print(f"Using Redis configuration: {redis_base}/{redis_db}")

        return cls(
            ER_CACHE_BASE=redis_base,
            ER_CACHE_DB=redis_db,
            API_KEY=os.environ.get("API_KEY"),
            DEBUG_MODE=False,
            # os.environ.get("DEBUG_MODE", "False").lower()
            # in ("true", "1", "yes"),
        )


# Create a singleton instance with validation
try:
    settings = AppSettings.from_env()
    print("Successfully loaded environment configuration")
except Exception as e:
    print(f"Error loading environment configuration: {e}")
    raise
