from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import load_config
from .creators import Creator, load_creators, match_creator, require_permission, resolve_permission
from .schedule import PLATFORMS, assign_slots
from .state import State


def _credit_text(creator: Creator, url: str) -> str:
    return f"🎥 Créditos: {creator.name} ({creator.handle}). Vídeo completo: {url}"


def process_source(cfg: dict[str, Any], state: State, *, video: Path, video_id: str, title: str,
                   url: str, creator: Creator) -> list[str]:
    from .highlights import select_highlights
    from .render import render_clip
    from .subtitles import build_ass, words_in_range
    from .transcribe import transcribe

    work, out = Path(cfg["work_dir"]), Path(cfg["output_dir"])
    w, llm, c = cfg.get("whisper", {}), cfg.get("llm", {}), cfg.get("clips", {})
    print(f"Transcribiendo {title}…")
    transcript = transcribe(video, work, model=w.get("model", "small"), device=w.get("device", "auto"),
                            language=cfg.get("language", "es"))
    print("Eligiendo highlights…")
    highlights = select_highlights(
        transcript, title=title, n=int(c.get("per_video", 4)), min_s=float(c.get("min_seconds", 20)),
        max_s=float(c.get("max_seconds", 59)), language=cfg.get("language", "es"),
        model=llm.get("model", "claude-opus-5-5"), effort=llm.get("effort", "medium"))

    status = "approved" if c.get("auto_approve") else "pending"
    ids = []
    for i, h in enumerate(highlights, 1):
        clip_id = f"{video_id}-{i:02d}"
        dest = out / "clips" / f"{clip_id}.mp4"
        print(f"Renderizando {clip_id} ({h.start:.0f}s–{h.end:.0f}s): {h.hook}")
        words = words_in_range(transcript, h.start, h.end)
        ass = build_ass(words, duration=h.end - h.start, style=cfg.get("style", {}), hook=h.hook,
                        credit=creator.handle)
        render_clip(video, dest, ass, h.start, h.end)
        state.clips[clip_id] = {
            "video_id": video_id, "file": str(dest), "start": h.start, "end": h.end, "hook": h.hook,
            "reason": h.reason, "score": h.score, "status": status, "creator": creator.name,
            "credit_text": _credit_text(creator, url),
            "copy": {p: getattr(h, p).model_dump() for p in PLATFORMS},
        }
        ids.append(clip_id)
    state.videos[video_id] = {"title": title, "url": url, "creator": creator.name,
                              "processed_at": datetime.now().isoformat(timespec="seconds"), "clips": ids}
    state.save()
    return ids


def cmd_process(cfg, state, args) -> None:
    from .download import download_video, video_info

    creators = load_creators(args.creators)
    for url in args.urls:
        info = video_info(url)
        creator = resolve_permission(creators, info, url)
        if info["id"] in state.videos and not args.force:
            print(f"Ya procesado: {info['title']} (usa --force para repetir)")
            continue
        video = download_video(url, cfg["work_dir"])
        process_source(cfg, state, video=video, video_id=info["id"], title=info["title"],
                       url=info.get("webpage_url", url), creator=creator)


def cmd_process_file(cfg, state, args) -> None:
    creators = load_creators(args.creators)
    creator = require_permission(match_creator(creators, name=args.creator), args.creator)
    path = Path(args.path)
    video_id = "f" + hashlib.sha1(path.name.encode()).hexdigest()[:10]
    process_source(cfg, state, video=path, video_id=video_id, title=args.title or path.stem,
                   url=args.url or creator.youtube_channel, creator=creator)


def cmd_watch(cfg, state, args) -> None:
    from .download import download_video, latest_videos, video_info

    d = cfg.get("download", {})
    lo, hi = float(d.get("min_minutes", 8)) * 60, float(d.get("max_minutes", 40)) * 60
    for creator in load_creators(args.creators):
        if not creator.permission:
            continue
        for entry in latest_videos(creator.youtube_channel, int(d.get("latest_per_channel", 3))):
            if entry["id"] in state.videos:
                continue
            dur = entry.get("duration") or 0
            if dur and not (lo <= dur <= hi):
                continue
            url = f"https://www.youtube.com/watch?v={entry['id']}"
            info = video_info(url)
            video = download_video(url, cfg["work_dir"])
            process_source(cfg, state, video=video, video_id=info["id"], title=info["title"], url=url,
                           creator=creator)


def cmd_discover(cfg, state, args) -> None:
    """Solo lista candidatos: tú decides cuáles procesar, porque hay resubidas con licencia CC falsa."""
    from .creators import is_reuse_licensed
    from .download import search_creative_commons, video_info

    d = cfg.get("download", {})
    lo, hi = float(d.get("min_minutes", 8)) * 60, float(d.get("max_minutes", 40)) * 60
    found = 0
    for entry in search_creative_commons(args.query, args.limit):
        dur = entry.get("duration") or 0
        if entry["id"] in state.videos or (dur and not (lo <= dur <= hi)):
            continue
        url = f"https://www.youtube.com/watch?v={entry['id']}"
        try:
            info = video_info(url)
        except Exception as e:  # vídeo privado, borrado o no disponible en tu país
            print(f"(saltado {url}: {str(e).splitlines()[0][:80]})")
            continue
        if not is_reuse_licensed(info):  # se comprueba la licencia vídeo a vídeo, no solo el filtro
            continue
        found += 1
        print(f"\n{info['title']}\n  canal: {info.get('channel')} ({info.get('channel_follower_count') or '?'} subs)"
              f"  ·  {int(info.get('duration', 0)) // 60} min  ·  {info.get('view_count', 0):,} vistas"
              f"\n  {url}\n  licencia: {info.get('license')}")
    if found:
        print("\nComprueba que el canal es el autor original (no una resubida) antes de usar: python -m shorts process URL")
    else:
        print("No he encontrado vídeos Creative Commons de esa duración. Prueba otra búsqueda.")


def cmd_review(cfg, state, args) -> None:
    pending = {k: v for k, v in state.clips.items() if v["status"] == "pending"}
    if not pending:
        print("No hay clips pendientes de revisión.")
    for cid, c in pending.items():
        print(f"\n{cid}  [{c['score']}/10]  {c['creator']}\n  gancho: {c['hook']}\n  motivo: {c['reason']}"
              f"\n  archivo: {c['file']}")


def _set_status(state: State, ids: list[str], status: str) -> None:
    targets = [k for k, v in state.clips.items() if v["status"] == "pending"] if ids == ["all"] else ids
    for cid in targets:
        if cid not in state.clips:
            print(f"No existe {cid}")
            continue
        state.clips[cid]["status"] = status
        print(f"{cid}: {status}")
    state.save()


def cmd_schedule(cfg, state, args) -> None:
    scheduled = {p["clip_id"] for p in state.posts}
    ready = sorted((k for k, v in state.clips.items() if v["status"] == "approved" and k not in scheduled),
                   key=lambda k: -state.clips[k]["score"])
    if not ready:
        print("No hay clips aprobados sin programar.")
        return
    taken: dict[str, set[str]] = {}
    for p in state.posts:
        taken.setdefault(p["platform"], set()).add(p["when"])
    new = assign_slots(ready, cfg.get("schedule", {}), cfg.get("timezone", "Europe/Madrid"), taken)
    for p in new:
        p["exported"] = False
        state.clips[p["clip_id"]]["status"] = "scheduled"
        print(f"{p['when'][:16].replace('T', ' ')}  {p['platform']:<9}  {p['clip_id']}")
    state.posts.extend(new)
    state.save()


def cmd_export(cfg, state, args) -> None:
    from .metricool import export_csv

    if cfg.get("metricool", {}).get("mode", "csv") != "csv":
        raise SystemExit("El modo api de Metricool aún no está implementado; usa mode: csv.")
    todo = [p for p in state.posts if not p.get("exported")]
    if not todo:
        print("Nada nuevo que exportar.")
        return
    name = f"metricool-{datetime.now():%Y%m%d-%H%M}.csv"
    path = export_csv(todo, state.clips, cfg, Path(cfg["output_dir"]) / "exports" / name)
    for p in todo:
        p["exported"] = True
    state.save()
    print(f"CSV listo para la carga masiva de Metricool: {path}")


def cmd_run(cfg, state, args) -> None:
    cmd_watch(cfg, state, args)
    if cfg.get("clips", {}).get("auto_approve"):
        cmd_schedule(cfg, state, args)
        cmd_export(cfg, state, args)
    else:
        cmd_review(cfg, state, args)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="shorts", description="Clips verticales de coaching, de vídeo largo a Metricool.")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--creators", default="creators.yaml")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("process", help="procesar uno o varios vídeos de YouTube")
    p.add_argument("urls", nargs="+")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_process)

    p = sub.add_parser("process-file", help="procesar un archivo local (p. ej. el que te pasa el creador)")
    p.add_argument("path")
    p.add_argument("--creator", required=True, help="nombre exacto en creators.yaml")
    p.add_argument("--title")
    p.add_argument("--url", help="enlace al vídeo original para los créditos")
    p.set_defaults(fn=cmd_process_file)

    sub.add_parser("watch", help="procesar vídeos nuevos de los canales autorizados").set_defaults(fn=cmd_watch)
    p = sub.add_parser("discover", help="buscar vídeos con licencia Creative Commons (reutilización permitida)")
    p.add_argument("query", help='p. ej. "motivación disciplina conferencia"')
    p.add_argument("--limit", type=int, default=30, help="resultados de búsqueda a revisar")
    p.set_defaults(fn=cmd_discover)

    sub.add_parser("review", help="ver clips pendientes").set_defaults(fn=cmd_review)
    for name, status in (("approve", "approved"), ("reject", "rejected")):
        p = sub.add_parser(name, help=f"marcar clips como {status} (ids o 'all')")
        p.add_argument("ids", nargs="+")
        p.set_defaults(fn=lambda cfg, st, a, s=status: _set_status(st, a.ids, s))
    sub.add_parser("schedule", help="asignar franjas a los clips aprobados").set_defaults(fn=cmd_schedule)
    sub.add_parser("export", help="generar CSV para Metricool").set_defaults(fn=cmd_export)
    sub.add_parser("run", help="watch + (si auto_approve) schedule + export").set_defaults(fn=cmd_run)

    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    args.fn(cfg, State(cfg["output_dir"]), args)


if __name__ == "__main__":
    main()
