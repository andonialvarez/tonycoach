from __future__ import annotations

import json
import statistics
import subprocess
from pathlib import Path

OUT_W, OUT_H = 1080, 1920


def probe_size(video: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "json", str(video)], capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"])


def face_center_x(video: Path, start: float, end: float, step: float = 1.0) -> float | None:
    """Centro horizontal (0-1) de la cara principal en el tramo, o None si no hay OpenCV/caras."""
    try:
        import cv2
    except ImportError:
        return None
    if not hasattr(cv2, "CascadeClassifier"):
        return None
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(str(video))
    xs: list[float] = []
    t = start
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6,
                                         minSize=(gray.shape[0] // 10, gray.shape[0] // 10))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            xs.append((x + w / 2) / frame.shape[1])
        t += step
    cap.release()
    return statistics.median(xs) if xs else None


def crop_x(src_w: int, src_h: int, center: float | None) -> tuple[int, int]:
    """Ancho de recorte 9:16 y posición x, centrado en la cara si se conoce."""
    cw = min(src_w, int(src_h * 9 / 16) // 2 * 2)
    c = 0.5 if center is None else center
    x = int(round(c * src_w - cw / 2))
    return cw, max(0, min(src_w - cw, x))


def escape_filter_path(path: Path) -> str:
    p = str(path.resolve()).replace("\\", "/")
    return p.replace(":", "\\:").replace("'", "\\'")


def build_ffmpeg_cmd(src: Path, out: Path, ass: Path, start: float, end: float, src_w: int, src_h: int,
                     center: float | None) -> list[str]:
    if src_w / src_h <= 9 / 16 + 0.01:  # ya vertical
        geo = f"scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=decrease,pad={OUT_W}:{OUT_H}:(ow-iw)/2:(oh-ih)/2"
    else:
        cw, x = crop_x(src_w, src_h, center)
        geo = f"crop={cw}:{src_h}:{x}:0,scale={OUT_W}:{OUT_H}"
    vf = f"{geo},setsar=1,ass='{escape_filter_path(ass)}'"
    return [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.2f}", "-i", str(src), "-t", f"{end - start:.2f}",
        "-vf", vf,
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", str(out),
    ]


def render_clip(src: Path, out: Path, ass_text: str, start: float, end: float) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    ass = out.with_suffix(".ass")
    ass.write_text(ass_text, encoding="utf-8")
    w, h = probe_size(src)
    center = face_center_x(src, start, end)
    subprocess.run(build_ffmpeg_cmd(src, out, ass, start, end, w, h, center), check=True)
    return out
