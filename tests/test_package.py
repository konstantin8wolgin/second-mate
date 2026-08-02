from __future__ import annotations

import importlib.util


def test_second_mate_is_an_importable_package() -> None:
    """Removing the packaged runtime must break the distribution contract."""
    assert importlib.util.find_spec("second_mate") is not None
