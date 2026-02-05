"""Configuration module for Robyn server.

Handles environment variables and settings for the Robyn runtime server.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


@dataclass
class ServerConfig:
    """Server configuration from environment variables."""

    host: str = "0.0.0.0"
    port: int = 8081
    workers: int = 1
    dev_mode: bool = False

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("ROBYN_HOST", "0.0.0.0"),
            port=int(os.getenv("ROBYN_PORT", "8081")),
            workers=int(os.getenv("ROBYN_WORKERS", "1")),
            dev_mode=os.getenv("ROBYN_DEV", "false").lower() in ("true", "1", "yes"),
        )


@dataclass
class SupabaseConfig:
    """Supabase configuration for authentication."""

    url: str = ""
    key: str = ""
    secret: str = ""
    jwt_secret: str = ""

    @classmethod
    def from_env(cls) -> "SupabaseConfig":
        """Load Supabase configuration from environment variables."""
        return cls(
            url=os.getenv("SUPABASE_URL", ""),
            key=os.getenv("SUPABASE_KEY", ""),
            secret=os.getenv("SUPABASE_SECRET", ""),
            jwt_secret=os.getenv("SUPABASE_JWT_SECRET", ""),
        )

    @property
    def is_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return bool(self.url and self.key)


@dataclass
class LLMConfig:
    """LLM configuration for agent execution."""

    openai_api_key: str = ""
    openai_api_base: str = ""
    model_name: str = ""

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load LLM configuration from environment variables."""
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_api_base=os.getenv("OPENAI_API_BASE", ""),
            model_name=os.getenv("MODEL_NAME", ""),
        )


@dataclass
class Config:
    """Complete application configuration."""

    server: ServerConfig
    supabase: SupabaseConfig
    llm: LLMConfig

    @classmethod
    def from_env(cls) -> "Config":
        """Load complete configuration from environment variables."""
        return cls(
            server=ServerConfig.from_env(),
            supabase=SupabaseConfig.from_env(),
            llm=LLMConfig.from_env(),
        )


# Global config instance (lazy-loaded)
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
