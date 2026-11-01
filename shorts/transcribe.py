from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def transcribe(video: Path, work_dir: str | Path, model: str = "small", device: str = "auto",
               language: str | None = "es") -> dict[str, Any]:
    """Transcribe con faster-whisper y marcas de tiempo por palabra. Cachea el resultado."""
    cache = Path(work_dir) / "transcripts" / f"{video.stem}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    from faster_whisper import WhisperModel

    compute = "int8" if device in ("cpu", "auto") else "float16"
    wm = WhisperModel(model, device=device, compute_type=compute)
    segments, info = wm.transcribe(str(video), language=language, word_timestamps=True, vad_filter=True)
    data = {
        "language": info.language,
        "duration": info.duration,
        "segments": [
            {
                "start": round(s.start, 2),
                "end": round(s.end, 2),
                "text": s.text.strip(),
                "words": [{"start": round(w.start, 2), "end": round(w.end, 2), "word": w.word.strip()}
                          for w in (s.words or []) if w.word.strip()],
            }
            for s in segments
        ],
    }
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data
