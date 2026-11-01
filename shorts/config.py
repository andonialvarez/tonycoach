from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"No encuentro {path}. Copia config.example.yaml como config.yaml.")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for key in ("work_dir", "output_dir"):
        Path(cfg.get(key, f"./{key.split('_')[0]}")).mkdir(parents=True, exist_ok=True)
    return cfg
