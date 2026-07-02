"""Continuous source-based knowledge builder for Hermes persona memory."""

from memory_builder.venv_bootstrap import ensure_project_venv

ensure_project_venv()

from memory_builder.paths import project_root

__all__ = ["project_root"]
