"""Re-exec scripts with the project .venv when invoked via system python3."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def ensure_project_venv() -> None:
    root = Path(__file__).resolve().parents[1]
    venv_dir = root / ".venv"
    venv_python = venv_dir / "bin" / "python3"
    if not venv_python.is_file():
        return

    try:
        already_venv = Path(sys.prefix).resolve() == venv_dir.resolve()
    except OSError:
        already_venv = False

    if already_venv:
        return

    os.execv(venv_python, [str(venv_python), *sys.argv])
