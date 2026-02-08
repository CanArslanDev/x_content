"""YAML configuration loader."""

from pathlib import Path

import yaml


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
_config: dict | None = None


def load_config() -> dict:
    """Load and cache config.yaml."""
    global _config
    if _config is None:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def get(key: str, default=None):
    """Get a top-level config value."""
    return load_config().get(key, default)
