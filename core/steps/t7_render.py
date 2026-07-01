"""
core/steps/t7_render.py — Render + post-processing step

Uses HyperFrames to render composition to video, then:
  1. Add audio (TTS)
  2. Burn subtitles (ASS)
  3. Final quality check
"""
import os, subprocess, json
from pathlib import Path
from core.steps.base import StepHandler, StepResult
from core.config import VIDEO_FPS, FILE_NAMES, resolve_episode_path
from core.subtitle import burn_subtitles


class RenderHandler(StepHandler):
    name = "T7"
    description = "Render compositions to video + add audio + subtitles"


    def pre_condition(self):
        """Verify composition exists and HyperFrames can find entry point."""
        err = super().pre_condition()
        if err:
            return err
        comp_path = self.episode_dir / FILE_NAMES["composition"]
        if not comp_path.exists():
            return f"Composition file {comp_path} 不存在。请先运行 T6。"
        # Always use the full composition (with GSAP) for HyperFrames rendering
        # The preview index.html from T6 is GSAP-free and won't animate.
        import shutil
        shutil.copy2(str(comp_path), idx_path := self.episode_dir / "index.html")
        print(f"  🔗 index.html updated from composition for HyperFrames rendering")
        return None

    def execute(self) -> StepResult:
        episode_dir = self.episode_dir
        video_dir = episode_dir / FILE_NAMES["final_dir"]
        video_dir.mkdir(exist_ok=True)

        # Step 1: HyperFrames render
        raw_video = str(episode_dir / FILE_NAMES["raw_video"])
        print(f"  Rendering with HyperFrames (fps={VIDEO_FPS})...")
        r = subprocess.run(
            ["npx", "hyperframes", "render"],
            cwd=str(episode_dir), capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            return StepResult(False, errors=[f"HyperFrames render failed: {r.stderr[:500]}"])
        # npx hyperframes render saves to renders/ dir, find the latest
        renders_dir = episode_dir / "renders"
        if renders_dir.exists():
            renders = sorted(renders_dir.glob("*.mp4"))
        else:
            renders = []
        if not renders:
            return StepResult(False, errors=["Render produced no MP4 output"])
        latest = str(renders[-1])
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
        audio_path = Path(resolve_episode_path(str(episode_dir), "audio_narration"))
        video_with_audio = str(episode_dir / FILE_NAMES["video_with_audio"])
        if audio_path.exists():
            print("  Adding audio...")
            subprocess.run([
                "ffmpeg", "-y", "-i", raw_video, "-i", str(audio_path),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                video_with_audio,
            ], capture_output=True, timeout=300, check=True)

            # Step 3: Burn subtitles
            ass_path = Path(resolve_episode_path(str(episode_dir), "audio_ass"))
            final_video = str(episode_dir / FILE_NAMES["final_video"])
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
            final_video = str(episode_dir / FILE_NAMES["final_video"])
            subprocess.run(["cp", raw_video, final_video], check=True)
            print("  No audio found — video will be silent")

        # Restore index.html as preview (remove GSAP, add navigation)
        comp_path = episode_dir / FILE_NAMES["composition"]
        idx_path = episode_dir / "index.html"
        if comp_path.exists():
            _pv = comp_path.read_text(encoding="utf-8")
            _shim_marker = 'inlined: assets/timeline-shim.js'
            _shim_start = _pv.find(f'<script>/* {_shim_marker} */')
            if _shim_start >= 0:
                _shim_end = _pv.find('</script>', _shim_start)
                if _shim_end >= 0:
                    _pv = _pv[:_shim_start] + _pv[_shim_end + len('</script>'):]
            _tl_marker = 'window.__timelines'
            _tl_start = _pv.find('<script>')
            while _tl_start >= 0:
                _tl_end = _pv.find('</script>', _tl_start)
                if _tl_end < 0:
                    break
                if _tl_marker in _pv[_tl_start:_tl_end]:
                    _pv = _pv[:_tl_start] + _pv[_tl_end + len('</script>'):]
                    break
                _tl_start = _pv.find('<script>', _tl_end + 1)
            _dm_start = _pv.find('<!-- Danmaku overlay -->')
            if _dm_start >= 0:
                _close_start = _pv.find('<div', _dm_start)
                if _close_start >= 0:
                    depth, pos = 0, _close_start
                    while pos < len(_pv):
                        _no = _pv.find('<div ', pos + 1)
                        _nc = _pv.find('</div>', pos + 1)
                        if _nc < 0:
                            break
                        if _no >= 0 and _no < _nc:
                            depth += 1; pos = _no + 5
                        else:
                            if depth == 0:
                                _pv = _pv[:_dm_start] + _pv[_nc + 6:]; break
                            depth -= 1; pos = _nc + 6
            _pv = _pv.replace('content="width=1920, height=1080"', 'content="width=device-width, initial-scale=1.0"')
            _nav = (
                '<style>'
                '.danmaku,.danmaku-overlay{display:none!important}'
                'body{transform-origin:top left;overflow:hidden;margin:0;}'
                '#_preview-nav{position:fixed;bottom:28px;right:28px;z-index:99999;'
                'display:flex;align-items:center;gap:8px;'
                'background:rgba(0,0,0,0.4);color:#fff;padding:6px 16px 6px 12px;'
                'border-radius:999px;font:13px/1.4 sans-serif;user-select:none;'
                'pointer-events:auto;backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);}'
                '#_preview-nav button{background:rgba(255,255,255,0.2);border:none;color:#fff;'
                'width:28px;height:28px;border-radius:50%;cursor:pointer;'
                'font:16px/1 sans-serif;display:flex;align-items:center;justify-content:center;transition:background .15s;}'
                '#_preview-nav button:hover{background:rgba(255,255,255,0.35);}'
                '#_preview-nav ._pc{min-width:32px;text-align:center;font-variant-numeric:tabular-nums;}'
                '</style>'
                '<script>'
                '(function(){'
                'var ps=document.querySelectorAll(\'[id^="s"]\');if(!ps.length)return;'
                'var c=0;'
                'function g(n){if(n<0||n>=ps.length)return;ps[c].style.opacity=\'0\';c=n;ps[c].style.opacity=\'1\';}'
                'document.addEventListener(\'keydown\',function(e){'
                'if(e.key==\'ArrowRight\'||e.key==\'ArrowDown\'||e.key==\' \'){e.preventDefault();g(c+1)}'
                'if(e.key==\'ArrowLeft\'||e.key==\'ArrowUp\'){e.preventDefault();g(c-1)'
                '}});'
                'document.addEventListener(\'click\',function(e){if(e.target.closest(\'#_preview-nav\'))return;g(c+1)});'
                'function fit(){var sx=window.innerWidth/1920,sy=window.innerHeight/1080,s=Math.min(sx,sy);'
                'document.body.style.transform=\'scale(\'+s+\')\';'
                'document.body.style.width=1920/s+\'px\';'
                'document.body.style.height=1080/s+\'px\';}'
                'window.addEventListener(\'resize\',fit);fit();'
                'var nav=document.createElement(\'div\');nav.id=\'_preview-nav\';'
                'nav.innerHTML=\'<button onclick="g(Math.max(0,c-1))">&larr;</button>'
                '<span class="_pc">1/\'+ps.length+\'</span>'
                '<button onclick="g(Math.min(ps.length-1,c+1))">&rarr;</button>\';'
                'document.body.appendChild(nav);'
                'var _g=g;g=function(n){_g(n);var pc=nav.querySelector(\'._pc\');if(pc)pc.textContent=(c+1)+\'/\'+ps.length};'
                'g(0);})();'
                '</script>'
            )
            _pv = _pv.replace('</body>', _nav + '\n</body>')
            idx_path.write_text(_pv, encoding="utf-8")
            print(f"  🔗 index.html (preview restored — no GSAP, with navigation)")

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
