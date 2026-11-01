from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Creator:
    name: str
    handle: str
    youtube_channel: str
    permission: bool
    permission_note: str = ""


def load_creators(path: str | Path = "creators.yaml") -> list[Creator]:
    path = Path(path)
    if not path.exists():
        raise SystemExit(f"No encuentro {path}. Copia creators.example.yaml como creators.yaml.")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [Creator(**c) for c in data.get("creators", [])]


def _norm(url: str) -> str:
    return url.strip().lower().rstrip("/").replace("http://", "https://").replace("://m.", "://www.")


def match_creator(creators: list[Creator], *, channel_url: str = "", uploader_id: str = "",
                  name: str = "") -> Creator | None:
    """Busca el creador por URL del canal, @handle o nombre."""
    candidates = {_norm(channel_url)} if channel_url else set()
    if uploader_id:
        handle = uploader_id if uploader_id.startswith("@") else f"@{uploader_id}"
        candidates.add(_norm(f"https://www.youtube.com/{handle}"))
    for c in creators:
        if _norm(c.youtube_channel) in candidates:
            return c
        if name and c.name.strip().lower() == name.strip().lower():
            return c
    return None


def require_permission(creator: Creator | None, source: str) -> Creator:
    if creator is None:
        raise PermissionError(f"{source}: el canal no está en creators.yaml. Añádelo solo si tienes permiso.")
    if not creator.permission:
        raise PermissionError(f"{source}: {creator.name} no tiene permission: true en creators.yaml.")
    return creator
