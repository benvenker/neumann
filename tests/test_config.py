import importlib
from pathlib import Path

import pytest


def reload_config_module():
    import sys
    sys.modules.pop("config", None)
    return importlib.import_module("config")


def test_config_defaults(tmp_path, monkeypatch):
    # Ensure no env leaks
    monkeypatch.delenv("ASSET_BASE_URL", raising=False)
    monkeypatch.delenv("CHROMA_PATH", raising=False)
    # Ensure key is treated as absent even if inherited from host env
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.delenv("LINES_PER_CHUNK", raising=False)
    monkeypatch.delenv("OVERLAP", raising=False)

    cfg_mod = reload_config_module()
    cfg = cfg_mod.config

    assert str(cfg.ASSET_BASE_URL) == "http://127.0.0.1:8000"
    assert cfg.CHROMA_PATH == "./chroma_data"
    assert cfg.LINES_PER_CHUNK == 180
    assert cfg.OVERLAP == 30
    assert cfg.has_openai_key is False
    assert isinstance(cfg.chroma_path, Path)


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("ASSET_BASE_URL", "http://localhost:9000")
    monkeypatch.setenv("CHROMA_PATH", "/tmp/chroma")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("LINES_PER_CHUNK", "200")
    monkeypatch.setenv("OVERLAP", "20")

    cfg_mod = reload_config_module()
    cfg = cfg_mod.Config()  # instantiate fresh to pick up env

    assert str(cfg.ASSET_BASE_URL) == "http://localhost:9000"
    assert cfg.CHROMA_PATH == "/tmp/chroma"
    assert cfg.LINES_PER_CHUNK == 200
    assert cfg.OVERLAP == 20
    assert cfg.has_openai_key is True


def test_overlap_validation(monkeypatch):
    monkeypatch.setenv("LINES_PER_CHUNK", "50")
    monkeypatch.setenv("OVERLAP", "50")  # equal is invalid
    import pytest
    with pytest.raises(Exception):  # noqa: B017
        reload_config_module()


def test_require_openai(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg_mod = reload_config_module()
    cfg = cfg_mod.Config()

    with pytest.raises(Exception):  # noqa: B017
        cfg.require_openai()
