"""
Configuration management for the Monday.com BI Agent.

Loads and validates required environment variables on startup.
Fails fast with clear error messages if required keys are missing.
Supports both local .env files and Streamlit Cloud secrets.
"""

import os
from dotenv import load_dotenv
from typing import Optional


def _get_secret(key: str) -> Optional[str]:
    """
    Try to get a secret from Streamlit Cloud secrets, fall back to environment variable.
    
    Args:
        key: The environment variable name to look for.
        
    Returns:
        The secret value if found, None otherwise.
    """
    try:
        import streamlit as st
        # Check if st.secrets exists and has the key
        if hasattr(st, 'secrets') and st.secrets is not None:
            return st.secrets.get(key) or os.getenv(key)
        return os.getenv(key)
    except Exception:
        # Running locally without streamlit or secrets not available
        return os.getenv(key)


class Config:
    """
    Centralized configuration for the BI agent.
    
    Attributes:
        groq_api_key: API key for Groq LLM service.
        monday_api_token: API token for Monday.com GraphQL API.
    """
    # singletons used by ``get_instance``
    _instance: "Optional[Config]" = None
    
    def __init__(self):
        """Load and validate all required environment variables."""
        # Load .env file if present (for local development)
        load_dotenv()
        
        # Try to get from Streamlit Cloud secrets first, then fall back to environment
        self.groq_api_key = _get_secret("GROQ_API_KEY")
        self.monday_api_token = _get_secret("MONDAY_API_TOKEN")
        
        # Validate - at least one LLM key should be present
        self._validate()
    
    def _validate(self) -> None:
        """
        Validate that all required environment variables are set.
        
        Raises:
            ValueError: If any required key is missing or empty.
        """
        missing = []
        
        if not self.groq_api_key or not self.groq_api_key.strip():
            missing.append("GROQ_API_KEY")
        
        if not self.monday_api_token or not self.monday_api_token.strip():
            missing.append("MONDAY_API_TOKEN")
        
        if missing:
            raise ValueError(
                f"\n❌ Missing required environment variables: {', '.join(missing)}\n\n"
                f"Setup Instructions:\n"
                f"  1. Copy .env.example to .env (if you haven't already)\n"
                f"  2. Edit .env and fill in your actual API keys\n\n"
                f"Get your keys at:\n"
                f"  - GROQ_API_KEY: https://console.groq.com/keys\n"
                f"  - MONDAY_API_TOKEN: Monday.com Account → API Tokens\n"
            )
    
    @staticmethod
    def get_instance() -> "Config":
        """
        Get or create the singleton Config instance.
        
        Returns:
            Config instance with validated environment variables.
        """
        if Config._instance is None:
            Config._instance = Config()
        # mypy/pylance sometimes thinks this could be None
        return Config._instance  # type: ignore[return-value]


# Lazy-load config once on first import
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global Config instance.
    
    This is the recommended way to access configuration throughout the app.
    The config is validated once on first call; subsequent calls return
    the cached instance.
    
    Returns:
        Config instance with validated environment variables.
        
    Raises:
        ValueError: If required environment variables are missing.
    """
    global _config
    if _config is None:
        _config = Config()
    return _config
