from __future__ import annotations

import importlib.util
import tomllib
from importlib.resources import files
from pathlib import Path


def test_second_mate_is_an_importable_package() -> None:
    """Removing the packaged runtime must break the distribution contract."""
    assert importlib.util.find_spec("second_mate") is not None


def test_second_mate_distribution_declares_its_public_types() -> None:
    """Removing py.typed must break the configured package-level mypy contract."""

    assert files("second_mate").joinpath("py.typed").is_file()


def test_source_distribution_manifest_includes_operator_contracts() -> None:
    """Every supported operator entrypoint must ship with its exact usage contract."""
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    included = project["tool"]["hatch"]["build"]["targets"]["sdist"]["include"]

    assert "/docs/second-mate/CONVERSATION-HANDOFF.md" in included
