"""
v3/models.py — Data models for pipeline artifacts
"""
from dataclasses import dataclass, field
from typing import Optional


# ── Timeline / Slide Models ──

@dataclass
class SlideTiming:
    page: int
    start: float
    end: float
    duration: float
    title: str = ""


@dataclass
class TimelineArtifact:
    total_duration: float
    slides: list[SlideTiming] = field(default_factory=list)

    def validate(self) -> list[str]:
        errors = []
        if not self.slides:
            errors.append("No slides defined")
            return errors
        pos = 0.0
        for s in self.slides:
            if abs(s.start - pos) > 0.01:
                errors.append(f"P{s.page} start={s.start} != expected {pos}")
            pos = s.end
        if abs(self.total_duration - pos) > 0.1:
            errors.append(f"Total duration {self.total_duration} != sum {pos}")
        return errors


# ── Image Models ──

@dataclass
class ImageSlot:
    page: int
    slot: str
    layout: str
    source: str = "ai"
    prompt: str = ""
    filename: str = ""
    size: str = "auto"


# ── Composition Models ──

@dataclass
class PageSpec:
    page: int
    layout: str
    title: str = ""
    subtitle: str = ""
    badge: str = ""
    emoji: str = ""
    elements: list[dict] = field(default_factory=list)
    duration: float = 10.0
    start: float = 0.0
    image_slot_name: str = ""
    code_text: str = ""
    code_language: str = ""
    narration: str = ""


# ── TTS / Audio ──

@dataclass
class SubtitleSegment:
    index: int
    start: float
    end: float
    text: str


@dataclass
class SubtitleArtifact:
    srt_path: str
    segments: list[SubtitleSegment] = field(default_factory=list)


# ── Video ──

@dataclass
class VideoArtifact:
    video_path: str
    final_path: str = ""
    duration: float = 0.0
    has_audio: bool = False

