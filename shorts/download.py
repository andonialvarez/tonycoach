from __future__ import annotations

from pathlib import Path
from typing import Any


def video_info(url: str) -> dict[str, Any]:
    import yt_dlp

    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        return ydl.extract_info(url, download=False)


def download_video(url: str, work_dir: str | Path) -> Path:
    """Descarga el vídeo (máx. 1080p) como mp4 y devuelve la ruta."""
    import yt_dlp

    out = Path(work_dir) / "videos"
    out.mkdir(parents=True, exist_ok=True)
    opts = {
        "quiet": True,
        "format": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/b",
        "merge_output_format": "mp4",
        "outtmpl": str(out / "%(id)s.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return Path(ydl.prepare_filename(info)).with_suffix(".mp4")


def latest_videos(channel_url: str, limit: int) -> list[dict[str, Any]]:
    """Lista los vídeos más recientes de un canal (sin descargar)."""
    import yt_dlp

    url = channel_url.rstrip("/") + "/videos"
    opts = {"quiet": True, "extract_flat": True, "playlistend": limit}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return [e for e in (info.get("entries") or []) if e.get("id")]


CC_FILTER = "EgIwAQ%3D%3D"  # filtro "Creative Commons" de la búsqueda de YouTube


def search_creative_commons(query: str, limit: int) -> list[dict[str, Any]]:
    """Busca en YouTube vídeos marcados como Creative Commons (sin descargar)."""
    import urllib.parse

    import yt_dlp

    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}&sp={CC_FILTER}"
    opts = {"quiet": True, "extract_flat": True, "playlistend": limit}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return [e for e in (info.get("entries") or []) if e.get("id")]
