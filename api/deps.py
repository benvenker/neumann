"""
FastAPI dependency injection providers.

Centralizes dependencies (DI) to keep endpoints decoupled from global imports.
"""

from chromadb.api import ClientAPI
from fastapi import Depends

from config import Config
from config import config as global_config
from indexer import get_client as get_chroma


def get_settings() -> Config:
    """
    FastAPI dependency to provide Config.

    Returns:
        Config: The global configuration instance.
    """
    return global_config


def get_chroma_client(cfg: Config = Depends(get_settings)) -> ClientAPI:
    """
    FastAPI dependency to provide ChromaDB client.

    Args:
        cfg: Configuration instance (injected)

    Returns:
        ClientAPI: ChromaDB client configured with CHROMA_PATH

    Note:
        cfg.CHROMA_PATH is already normalized to an absolute path by the config validator.
        This ensures the API and CLI use the same ChromaDB location.
    """
    return get_chroma(path=cfg.CHROMA_PATH)
