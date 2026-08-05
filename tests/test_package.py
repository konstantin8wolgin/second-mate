from __future__ import annotations

import importlib.util
from importlib.resources import files


def test_second_mate_is_an_importable_package() -> None:
    """Removing the packaged runtime must break the distribution contract."""
    assert importlib.util.find_spec("second_mate") is not None


def test_second_mate_distribution_declares_its_public_types() -> None:
    """Removing py.typed must break the configured package-level mypy contract."""

    assert files("second_mate").joinpath("py.typed").is_file()
