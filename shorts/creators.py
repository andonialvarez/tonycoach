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


def is_reuse_licensed(info: dict) -> bool:
    """True si YouTube marca el vídeo con licencia Creative Commons (CC BY: reutilización permitida)."""
    return "creative commons" in (info.get("license") or "").lower()


def resolve_permission(creators: list[Creator], info: dict, source: str) -> Creator:
    """Permite el vídeo si el canal está autorizado o si el propio vídeo tiene licencia Creative Commons."""
    c = match_creator(creators, channel_url=info.get("channel_url", ""),
                      uploader_id=info.get("uploader_id", ""), name=info.get("channel", ""))
    if c and c.permission:
        return c
    if is_reuse_licensed(info):
        handle = info.get("uploader_id") or ""
        if handle and not handle.startswith("@"):
            handle = f"@{handle}"
        return Creator(
            name=c.name if c else (info.get("channel") or info.get("uploader") or "Autor original"),
            handle=c.handle if c else (handle or info.get("channel") or ""),
            youtube_channel=info.get("channel_url", ""),
            permission=True,
            permission_note=f"Licencia del vídeo: {info.get('license')}",
        )
    return require_permission(c, source)
