from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class State:
    """Registro en JSON de vídeos procesados, clips y publicaciones programadas."""

    def __init__(self, output_dir: str | Path):
        self.path = Path(output_dir) / "state.json"
        self.data: dict[str, Any] = {"videos": {}, "clips": {}, "posts": []}
        if self.path.exists():
            self.data.update(json.loads(self.path.read_text(encoding="utf-8")))

    @property
    def videos(self) -> dict[str, Any]:
        return self.data["videos"]

    @property
    def clips(self) -> dict[str, Any]:
        return self.data["clips"]

    @property
    def posts(self) -> list[dict[str, Any]]:
        return self.data["posts"]

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)
