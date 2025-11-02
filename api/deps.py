"""
FastAPI dependency injection providers.

Centralizes dependencies (DI) to keep endpoints decoupled from global imports.
"""

from config import Config
from config import config as global_config


def get_settings() -> Config:
    """
    FastAPI dependency to provide Config.

    Returns:
        Config: The global configuration instance.

    TODO(nm-3573.2): Add get_chroma_client() for ChromaDB dependency injection.
    """
    return global_config
