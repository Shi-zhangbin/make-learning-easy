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
from v3.config import EDGE_TTS_VOICE, EDGE_TTS_RATE, VIDEO_FPS, FILE_NAMES
from v3.subtitle import generate_srt, srt_to_ass


class TTSHandler(StepHandler):
    name = "TTS"
    description = "Generate TTS audio + subtitles + timeline"


    def pre_condition(self):
        """Verify script has page markers for multi-slide timeline."""
        err = super().pre_condition()
        if err:
            return err
        try:
            script_path = self._get_script()
        except FileNotFoundError as e:
            return str(e)
        with open(script_path, encoding="utf-8") as f:
            content = f.read()
        import re
        page_markers = re.findall(r'^---+\s*P\d+', content, re.MULTILINE)
        if len(page_markers) < 2:
            return (
                f"脚本只有 {len(page_markers)} 个分页标记，需要至少 2 个。\n"
                f"口播稿必须包含 --- P1, --- P2 格式的分页标记。\n"
                f"文件: {script_path}"
            )
        return None

    def _get_script(self) -> str:
        """Find the narration script file in the episode directory."""
        # Try new naming first
        p = self.episode_dir / FILE_NAMES["script"]
        if p.exists():
            return str(p)
        # Try legacy names
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
        audio_dir = self.episode_dir / "03-audio"
        audio_dir.mkdir(exist_ok=True)
        # Legacy compat: also ensure audio/ exists
        legacy_audio = self.episode_dir / "audio"
        legacy_audio.mkdir(exist_ok=True)
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
            stripped = line.strip()
            # Page markers
            if re.match(r'^---+\s*P\d+', stripped):
                continue
            # Separators
            if re.match(r'^[-═=]{3,}$', stripped):
                continue
            # Stage directions in parentheses: （开场）（停顿）（完）
            if re.match(r'^[（(][^）)]{1,10}[）)]\s*$', stripped):
                continue
            # Numbered section headers: 一、xxx, 二、xxx, 三、xxx
            if re.match(r'^[一二三四五六七八九十]+[、.．]\s*\S', stripped):
                continue
            # Standalone section header like "收尾"
            if stripped in ("收尾", "开场白", "结束语", "结语"):
                continue
            # Metadata header lines: first 3 lines that look like metadata
            # (handled by pattern above for specific cases)
            clean_lines.append(line)
        full_script = "\n".join(clean_lines)
        
        # Write a clean version for reference
        clean_path = str(self.episode_dir / FILE_NAMES['script_raw'])
        with open(clean_path, 'w', encoding='utf-8') as f:
            f.write(full_script)

        # Measure rate from first 80 chars
        sample = full_script.strip()[:80] or "今天我们来学习人工智能的基础知识。"
        rate = self._measure_rate(sample)
        print(f"  TTS rate: {rate:.2f} chars/sec (sample: '{sample[:30]}...')")

        # Generate full TTS
        audio_path = str(audio_dir / FILE_NAMES["audio_narration"].split("/")[-1])
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
        ass_path = str(audio_dir / FILE_NAMES["audio_ass"].split("/")[-1])
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
                _nt = m.group(2).strip()
                chars = len(_nt)
                dur = (chars / max(total_chars, 1)) * total_dur if total_chars > 0 else total_dur / len(page_matches)
                _title = re.split(r'[。！？\n]', _nt)[0][:30]
                _title = _title + "…" if len(_title) >= 30 else _title if _title else f"P{pg}"
                pages.append({"page": pg, "duration": round(dur, 2), "start": round(pos, 2),
                              "end": round(pos + dur, 2), "title": _title, "chars": chars,
                              "narration": _nt})
                pos += dur
        else:
            # No page markers: treat as one slide
            pages.append({"page": 1, "duration": round(total_dur, 2),
                          "start": 0.0, "end": round(total_dur, 2),
                          "title": "Full", "chars": len(full_script)})

        # Write timeline.json
        timeline = {"total_duration": round(total_dur, 2), "slides": pages,
                     "effective_rate": round(rate, 2)}
        tl_path = self.episode_dir / FILE_NAMES["timeline"]
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
