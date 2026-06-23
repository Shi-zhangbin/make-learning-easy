"""
v3/steps/t7_render.py — Render + post-processing step

Uses HyperFrames to render composition to video, then:
  1. Add audio (TTS)
  2. Burn subtitles (ASS)
  3. Final quality check
"""
import os, subprocess, json
from pathlib import Path
from v3.steps.base import StepHandler, StepResult
from v3.config import VIDEO_FPS
from v3.subtitle import burn_subtitles


class RenderHandler(StepHandler):
    name = "T7"
    description = "Render compositions to video + add audio + subtitles"

    def execute(self) -> StepResult:
        episode_dir = self.episode_dir
        video_dir = episode_dir / "成品"
        video_dir.mkdir(exist_ok=True)

        # Step 1: HyperFrames render
        raw_video = str(video_dir / "raw.mp4")
        print(f"  Rendering with HyperFrames (fps={VIDEO_FPS})...")
        r = subprocess.run(
            ["npx", "hyperframes", "render"],
            cwd=str(episode_dir), capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            return StepResult(False, errors=[f"HyperFrames render failed: {r.stderr[:500]}"])
        # npx hyperframes render saves to renders/ dir, find the latest
        import glob
        renders = sorted(glob.glob(str(episode_dir / "renders" / "*.mp4")))
        if not renders:
            return StepResult(False, errors=["Render produced no MP4 output"])
        latest = renders[-1]
        subprocess.run(["cp", latest, raw_video], check=True)

        if r.returncode != 0:
            # Check for common errors
            err = r.stderr.lower()
            if "window.__hf" in err or "not ready" in err:
                return StepResult(False, errors=[
                    "HyperFrames render failed: window.__hf not ready. "
                    "Check that all compositions have __hf registered."
                ])
            return StepResult(False, errors=[
                f"HyperFrames render failed: {r.stderr[:500]}"
            ])

        if not os.path.exists(raw_video) or os.path.getsize(raw_video) < 1000:
            return StepResult(False, errors=["Render produced no valid video output"])

        raw_size_mb = os.path.getsize(raw_video) / (1024 * 1024)
        print(f"  Raw video: {raw_size_mb:.1f}MB")

        # Step 2: Add audio
        audio_path = episode_dir / "audio" / "narration.mp3"
        video_with_audio = str(video_dir / "with_audio.mp4")
        if audio_path.exists():
            print("  Adding audio...")
            subprocess.run([
                "ffmpeg", "-y", "-i", raw_video, "-i", str(audio_path),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                video_with_audio,
            ], capture_output=True, timeout=300, check=True)

            # Step 3: Burn subtitles
            ass_path = episode_dir / "audio" / "narration.ass"
            final_video = str(video_dir / "final.mp4")
            if ass_path.exists():
                print("  Burning subtitles...")
                try:
                    burn_subtitles(video_with_audio, str(ass_path), final_video)
                except Exception as e:
                    print(f"  Subtitle burn failed, skipping: {e}")
                    # Fallback: copy video with audio but no subs
                    subprocess.run(["cp", video_with_audio, final_video], check=True)
            else:
                subprocess.run(["cp", video_with_audio, final_video], check=True)
        else:
            final_video = str(video_dir / "final.mp4")
            subprocess.run(["cp", raw_video, final_video], check=True)
            print("  No audio found — video will be silent")

        # Final info
        r = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration,size", "-of", "csv=p=0", final_video,
        ], capture_output=True, text=True, timeout=10)
        parts = r.stdout.strip().split(",")
        final_dur = float(parts[0]) if parts else 0
        final_size = int(parts[1]) if len(parts) > 1 else 0

        print(f"  ✅ Final video: {final_video}")
        print(f"     Duration: {final_dur:.1f}s")
        print(f"     Size: {final_size / (1024*1024):.1f}MB")

        return StepResult(True, {
            "raw_video": raw_video,
            "video_with_audio": video_with_audio if audio_path.exists() else "",
            "final_video": final_video,
            "duration": final_dur,
            "size_mb": round(final_size / (1024*1024), 1),
            "has_audio": audio_path.exists(),
        })

    def post_gate(self, result: StepResult) -> list[str]:
        issues = []
        final = result.artifact.get("final_video", "")
        if final and not os.path.exists(final):
            issues.append(f"Final video not found: {final}")
        if result.artifact.get("duration", 0) < 5:
            issues.append(f"Video too short: {result.artifact.get('duration', 0)}s")

        # Check for black frames
        if final and os.path.exists(final):
            dur = result.artifact.get("duration", 0)
            if dur > 3:
                mid = dur / 2
                r = subprocess.run([
                    "ffmpeg", "-y", "-ss", str(mid), "-i", final,
                    "-vframes", "1", "-vf", "format=gray,metadata=mean",
                    "-f", "null", "-",
                ], capture_output=True, text=True, timeout=30)
                if "mean:0" in r.stderr:
                    issues.append(f"Black frame detected at t={mid:.0f}s")

        return issues
