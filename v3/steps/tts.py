"""
v3/steps/tts.py — TTS + Subtitle generation step

Generates:
  1. Full TTS audio from narration script (edge-tts)
  2. SRT subtitles via whisper
  3. ASS subtitles for embedding
  4. timeline.json with per-slide durations
"""
import os, json, subprocess, tempfile, re
from pathlib import Path
from v3.steps.base import StepHandler, StepResult
from v3.config import EDGE_TTS_VOICE, EDGE_TTS_RATE, VIDEO_FPS
from v3.subtitle import generate_srt, srt_to_ass


class TTSHandler(StepHandler):
    name = "TTS"
    description = "Generate TTS audio + subtitles + timeline"

    def _get_script(self) -> str:
        """Find the narration script file in the episode directory."""
        candidates = [
            "配音稿_分段.txt", "配音稿.txt", "narration.txt",
            "口播稿.txt", "02_口播稿/口播稿.txt", "03_口播稿.txt",
        ]
        for c in candidates:
            p = self.episode_dir / c
            if p.exists():
                return str(p)
        # Walk all files for txt
        for f in sorted(self.episode_dir.rglob("*.txt")):
            return str(f)
        raise FileNotFoundError("No narration script found in episode directory")

    def _measure_rate(self, sample: str) -> float:
        """Measure TTS speaking rate with a short sample."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
            tmp = tf.name
        try:
            subprocess.run([
                "python3", "-m", "edge_tts",
                "--voice", EDGE_TTS_VOICE,
                "--rate", EDGE_TTS_RATE,
                "-t", sample,
                "--write-media", tmp,
            ], capture_output=True, timeout=60, check=True)
            r = subprocess.run([
                "ffprobe", "-v", "error", "-show_entries",
                "format=duration", "-of", "csv=p=0", tmp,
            ], capture_output=True, text=True, timeout=10)
            dur = float(r.stdout.strip())
            chars = len(re.findall(r'[\u4e00-\u9fff\w]', sample))
            return chars / max(dur, 0.1)
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def execute(self) -> StepResult:
        script_path = self._get_script()
        audio_dir = self.episode_dir / "audio"
        audio_dir.mkdir(exist_ok=True)

        with open(script_path, encoding="utf-8") as f:
            raw_script = f.read()
        
        # First, parse page markers from raw script
        import re
        page_pattern = re.compile(r"---\s*P(\d+).*?---\s*\n(.*?)(?=\n---\s*P|\Z)", re.DOTALL)
        page_matches = list(page_pattern.finditer(raw_script))
        
        # Strip page markers for TTS
        clean_lines = []
        for line in raw_script.split("\n"):
            if re.match(r'^---+\s*P\d+', line.strip()):
                continue
            if line.strip() == '---':
                continue
            clean_lines.append(line)
        full_script = "\n".join(clean_lines)
        
        # Write a clean version for reference
        clean_path = script_path.replace('.txt', '_纯文字.txt')
        with open(clean_path, 'w', encoding='utf-8') as f:
            f.write(full_script)

        # Measure rate from first 80 chars
        sample = full_script.strip()[:80] or "今天我们来学习人工智能的基础知识。"
        rate = self._measure_rate(sample)
        print(f"  TTS rate: {rate:.2f} chars/sec (sample: '{sample[:30]}...')")

        # Generate full TTS
        audio_path = str(audio_dir / "narration.mp3")
        print(f"  Generating TTS audio ({len(full_script)} chars)...")
        subprocess.run([
            "python3", "-m", "edge_tts",
            "--voice", EDGE_TTS_VOICE,
            "--rate", EDGE_TTS_RATE,
            "-f", clean_path,
            "--write-media", audio_path,
        ], capture_output=True, timeout=600, check=True)

        # Measure duration
        r = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "csv=p=0", audio_path,
        ], capture_output=True, text=True, timeout=10)
        total_dur = float(r.stdout.strip())

        print(f"  Audio duration: {total_dur:.1f}s")

        # Generate subtitles via whisper
        print("  Generating subtitles (whisper)...")
        sub_art = generate_srt(audio_path, str(audio_dir))

        # Generate ASS subtitles for embedding
        ass_path = str(audio_dir / "narration.ass")
        srt_to_ass(sub_art.srt_path, ass_path)

        print(f"  Subtitles: {len(sub_art.segments)} segments → {ass_path}")

        # Calculate per-page durations based on subtitle segments
        # Distribute total duration proportionally by page in narration
        pages = []
        # Parse script for page markers (--- P1 ... --- patterns)
        page_pattern = re.compile(r"---\s*P(\d+).*?---\s*\n(.*?)(?=\n---\s*P|\Z)", re.DOTALL)

        if page_matches:
            total_chars = sum(len(m.group(2).strip()) for m in page_matches)
            pos = 0.0
            for i, m in enumerate(page_matches):
                pg = int(m.group(1))
                chars = len(m.group(2).strip())
                dur = (chars / max(total_chars, 1)) * total_dur if total_chars > 0 else total_dur / len(page_matches)
                pages.append({"page": pg, "duration": round(dur, 2), "start": round(pos, 2),
                              "end": round(pos + dur, 2), "title": f"P{pg}", "chars": chars})
                pos += dur
        else:
            # No page markers: treat as one slide
            pages.append({"page": 1, "duration": round(total_dur, 2),
                          "start": 0.0, "end": round(total_dur, 2),
                          "title": "Full", "chars": len(full_script)})

        # Write timeline.json
        timeline = {"total_duration": round(total_dur, 2), "slides": pages,
                     "effective_rate": round(rate, 2)}
        tl_path = self.episode_dir / "timeline.json"
        with open(tl_path, "w", encoding="utf-8") as f:
            json.dump(timeline, f, ensure_ascii=False, indent=2)
        print(f"  Timeline: {tl_path} ({len(pages)} slides)")

        return StepResult(True, {
            "audio_path": audio_path,
            "total_duration": total_dur,
            "srt_path": sub_art.srt_path,
            "ass_path": ass_path,
            "timeline_path": str(tl_path),
            "slides": pages,
            "segments": len(sub_art.segments),
        })

    def post_gate(self, result: StepResult) -> list[str]:
        issues = []
        audio = result.artifact.get("audio_path", "")
        if audio and not os.path.exists(audio):
            issues.append(f"Audio file missing: {audio}")
        srt = result.artifact.get("srt_path", "")
        if srt and not os.path.exists(srt):
            issues.append(f"SRT file missing: {srt}")
        if result.artifact.get("total_duration", 0) < 1:
            issues.append(f"Audio too short: {result.artifact.get('total_duration', 0)}s")
        return issues
