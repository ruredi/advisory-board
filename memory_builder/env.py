from __future__ import annotations

import os
from pathlib import Path


_LOADED = False


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _apply_env(values: dict[str, str], *, overwrite: bool = False) -> None:
    for key, value in values.items():
        if overwrite or key not in os.environ or not os.environ[key].strip():
            os.environ[key] = value


def load_project_env(root: Path | None = None) -> None:
    """Load local .env, then secret-project .env as fallback for shared keys."""
    global _LOADED
    if _LOADED:
        return

    from memory_builder.paths import project_root

    base = root or project_root()
    _apply_env(_parse_env_file(base / ".env"))

    # Secret Project uses SCRAPFLY_API_KEY; scrapfly-scrapers expect SCRAPFLY_KEY.
    if not os.environ.get("SCRAPFLY_KEY", "").strip():
        secret_env = _parse_env_file(base.parent / "secret-project" / ".env")
        if secret_env.get("SCRAPFLY_API_KEY"):
            os.environ["SCRAPFLY_KEY"] = secret_env["SCRAPFLY_API_KEY"]
        _apply_env(secret_env, overwrite=False)

    _LOADED = True
