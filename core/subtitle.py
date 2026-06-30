"""
core/subtitle.py — Whisper subtitle generation

Uses whisper.cpp CLI (brew install whisper) to generate SRT subtitles
from audio files.
"""
import os, subprocess, json, re
from pathlib import Path
from core.config import FILE_NAMES
from core.models import SubtitleSegment, SubtitleArtifact


WHISPER_MODEL = "tiny"
WHISPER_LANG = "zh"


def generate_srt(audio_path: str, output_dir: str | None = None,
                 model: str = WHISPER_MODEL) -> SubtitleArtifact:
    """
    Transcribe audio to SRT subtitles using whisper.cpp CLI.
    """
    audio = Path(audio_path)
    if not audio.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    out_dir = Path(output_dir) if output_dir else audio.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    result = subprocess.run([
        "whisper", str(audio),
        "--model", model,
        "--language", WHISPER_LANG,
        "--output_format", "srt",
        "--output_dir", str(out_dir),
        "--verbose", "False",
    ], capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        raise RuntimeError(f"whisper failed: {result.stderr[:500]}")

    srt_name = audio.stem + ".srt"
    srt_path = out_dir / srt_name

    if not srt_path.exists():
        for f in out_dir.glob("*.srt"):
            srt_path = f
            break

    if not srt_path.exists():
        raise RuntimeError(f"SRT file not generated: checked {out_dir / srt_name}")

    segments = _parse_srt(str(srt_path))

    return SubtitleArtifact(
        srt_path=str(srt_path),
        segments=segments,
    )


def _parse_srt(srt_path: str) -> list[SubtitleSegment]:
    with open(srt_path, encoding="utf-8") as f:
        content = f.read()
    segments = []
    pattern = re.compile(
        r"(\d+)\n(\d{2}:\d{2}:\d{2}[,\.]\d{3}) --> (\d{2}:\d{2}:\d{2}[,\.]\d{3})\n(.+?)(?=\n\n|\Z)",
        re.DOTALL
    )
    for match in pattern.finditer(content):
        index = int(match.group(1))
        start = _srt_time_to_seconds(match.group(2))
        end = _srt_time_to_seconds(match.group(3))
        text = match.group(4).strip().replace("\n", " ")
        segments.append(SubtitleSegment(
            index=index, start=start, end=end, text=text
        ))
    return segments


def _srt_time_to_seconds(t: str) -> float:
    t = t.replace(",", ".")
    parts = t.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return float(t)


def srt_to_ass(srt_path: str, output_path: str,
               font_name: str = "sans-serif",
               font_size: int = 18,
               primary_color: str = "&H00FFFFFF",
               outline_color: str = "&H00000000",
               outline_width: int = 1,
               alignment: int = 2) -> str:
    segments = _parse_srt(srt_path)
    if not segments:
        raise ValueError("No subtitle segments to convert")

    ass_header = f"""[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{primary_color},{primary_color},{outline_color},{outline_color},0,0,1,{outline_width},0,{alignment},30,30,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events = []
    for seg in segments:
        start = _seconds_to_ass_time(seg.start)
        end = _seconds_to_ass_time(seg.end)
        text = seg.text.replace("\n", "\\N")
        events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    ass_content = ass_header + "\n".join(events)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    return output_path


def _seconds_to_ass_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"



def check_libass() -> bool:
    """Check if ffmpeg has libass/subtitles filter support."""
    import subprocess
    try:
        r = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True, timeout=5)
        return "subtitles" in r.stdout or "libass" in r.stdout
    except Exception:
        return False


def burn_subtitles(video_path: str, srt_or_ass_path: str,
                   output_path: str | None = None) -> str:
    if not output_path:
        p = Path(video_path)
        output_path = str(p.parent / (p.stem + "_subtitled" + p.suffix))

    sub_path = srt_or_ass_path
    if sub_path.endswith(".srt"):
        ass_path = sub_path.replace(".srt", ".ass")
        if not os.path.exists(ass_path):
            srt_to_ass(sub_path, ass_path)
        sub_path = ass_path

    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vf", f"subtitles={sub_path}",
        "-c:a", "copy",
        output_path,
    ], capture_output=True, timeout=600, check=True)

    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        art = generate_srt(sys.argv[1])
        print(f"SRT: {art.srt_path}")
        print(f"Segments: {len(art.segments)}")
        for s in art.segments[:5]:
            print(f"  [{s.start:.1f}s-{s.end:.1f}s] {s.text}")
    else:
        print("Usage: python3 -m core.subtitle <audio.mp3>")

