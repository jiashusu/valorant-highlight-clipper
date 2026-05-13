from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from .core import ClipSegment, hidden_subprocess_kwargs, resolve_tool


THUMBNAIL_WIDTH = 384
THUMBNAIL_HEIGHT = 216
CARD_PREVIEW_FPS = 30


class PreviewCache:
    def __init__(self, namespace: str = "valorant_clipper") -> None:
        root = Path(tempfile.gettempdir())
        self.thumbnail_cache_dir = root / f"{namespace}_thumbnails"
        self.card_preview_cache_dir = root / f"{namespace}_card_previews"

    def thumbnail_for(self, clip: ClipSegment, seek_seconds: float) -> Path:
        clip_path = Path(clip.path).expanduser().resolve()
        if not clip_path.exists():
            raise FileNotFoundError(clip_path)
        cache_dir = self.thumbnail_cache_dir / self.thumbnail_cache_key(clip, seek_seconds)
        cache_dir.mkdir(parents=True, exist_ok=True)
        thumbnail_path = cache_dir / "thumbnail.jpg"
        if thumbnail_path.exists():
            return thumbnail_path

        ffmpeg = resolve_tool("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg 不可用，无法生成低清预览")
        temporary_path = cache_dir / "thumbnail.raw.jpg"
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{seek_seconds:.3f}",
            "-i",
            str(clip_path),
            "-frames:v",
            "1",
            "-vf",
            f"scale={THUMBNAIL_WIDTH}:-2:flags=lanczos",
            "-q:v",
            "3",
            str(temporary_path),
        ]
        import subprocess

        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **hidden_subprocess_kwargs(),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "生成低清预览失败")
        with Image.open(temporary_path) as image:
            self.fit_thumbnail(image).save(thumbnail_path, quality=92)
        temporary_path.unlink(missing_ok=True)
        return thumbnail_path

    def card_preview_frames_for(self, clip: ClipSegment) -> list[Path]:
        clip_path = Path(clip.path).expanduser().resolve()
        if not clip_path.exists():
            raise FileNotFoundError(clip_path)
        cache_dir = self.card_preview_cache_dir / self.card_preview_cache_key(clip)
        cache_dir.mkdir(parents=True, exist_ok=True)
        frames = sorted(cache_dir.glob("frame_*.jpg"))
        if frames:
            return frames

        ffmpeg = resolve_tool("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg 不可用，无法生成卡片预览")
        temporary_dir = cache_dir / "tmp"
        if temporary_dir.exists():
            for old_frame in temporary_dir.glob("*.jpg"):
                old_frame.unlink()
        temporary_dir.mkdir(parents=True, exist_ok=True)
        command = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(clip_path),
            "-vf",
            f"fps={CARD_PREVIEW_FPS},scale={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT}:"
            "force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black",
            "-q:v",
            "3",
            str(temporary_dir / "frame_%05d.jpg"),
        ]
        import subprocess

        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **hidden_subprocess_kwargs(),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "生成卡片预览失败")
        frames = sorted(temporary_dir.glob("frame_*.jpg"))
        if not frames:
            raise RuntimeError("没有生成卡片预览帧")
        for frame in frames:
            frame.replace(cache_dir / frame.name)
        temporary_dir.rmdir()
        return sorted(cache_dir.glob("frame_*.jpg"))

    @staticmethod
    def thumbnail_seek_seconds(clip: ClipSegment, seconds_before: float) -> float:
        if clip.duration <= 0.3:
            return 0.0
        preferred = max(0.1, seconds_before)
        return min(preferred, max(0.0, clip.duration - 0.2))

    @staticmethod
    def thumbnail_cache_key(clip: ClipSegment, seek_seconds: float) -> str:
        clip_path = Path(clip.path).expanduser().resolve()
        stat = clip_path.stat()
        source = (
            f"{clip_path}:{stat.st_size}:{stat.st_mtime_ns}:"
            f"{THUMBNAIL_WIDTH}x{THUMBNAIL_HEIGHT}:{seek_seconds:.3f}:q=3"
        )
        return hashlib.sha1(source.encode("utf-8")).hexdigest()

    @staticmethod
    def card_preview_cache_key(clip: ClipSegment) -> str:
        clip_path = Path(clip.path).expanduser().resolve()
        stat = clip_path.stat()
        source = (
            f"{clip_path}:{stat.st_size}:{stat.st_mtime_ns}:"
            f"card_preview={THUMBNAIL_WIDTH}x{THUMBNAIL_HEIGHT}:fps={CARD_PREVIEW_FPS}:q=3"
        )
        return hashlib.sha1(source.encode("utf-8")).hexdigest()

    @staticmethod
    def fit_thumbnail(image: Image.Image) -> Image.Image:
        image = image.convert("RGB")
        image.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.BICUBIC)
        fitted = Image.new("RGB", (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), (16, 19, 29))
        left = (THUMBNAIL_WIDTH - image.width) // 2
        top = (THUMBNAIL_HEIGHT - image.height) // 2
        fitted.paste(image, (left, top))
        overlay = Image.new("RGBA", fitted.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        center_x = THUMBNAIL_WIDTH // 2
        center_y = THUMBNAIL_HEIGHT // 2
        draw.ellipse(
            (center_x - 24, center_y - 24, center_x + 24, center_y + 24),
            fill=(0, 0, 0, 120),
        )
        draw.polygon(
            [
                (center_x - 7, center_y - 14),
                (center_x - 7, center_y + 14),
                (center_x + 16, center_y),
            ],
            fill=(255, 255, 255, 230),
        )
        return Image.alpha_composite(fitted.convert("RGBA"), overlay).convert("RGB")
