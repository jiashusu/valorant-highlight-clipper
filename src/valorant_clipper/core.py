from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from .paths import resource_root, runtime_root


PROJECT_ROOT = resource_root()
RUNTIME_ROOT = runtime_root()
ASSET_DIR = PROJECT_ROOT / "assets" / "valorant_clipper"
NETWORK_PATH = ASSET_DIR / "valorant.npy"
MASK_PATH = ASSET_DIR / "valorant-mask.png"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".flv"}


def default_source_dir() -> Path:
    fallback = Path.home() / ("Videos" if os.name == "nt" else "Movies") / "VALORANT_CLIPS"
    return Path(os.getenv("VALORANT_CLIPS_DIR", str(fallback)))


DEFAULT_SOURCE_DIR = default_source_dir()
DEFAULT_OUTPUT_DIR = RUNTIME_ROOT / "outputs" / "valorant_highlights"
DEFAULT_EXCLUDES = {
    ".venv",
    "video_env",
    "__pycache__",
    ".git",
    ".idea",
    "node_modules",
    "无畏契约自动剪辑过后",
    "无畏契约排序过后",
    "pythonProject",
}


@dataclass
class VideoInfo:
    path: str
    name: str
    duration: float
    size_bytes: int


@dataclass
class ClipSegment:
    start: float
    end: float
    path: str
    name: str
    kills: int = 1

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["duration"] = self.duration
        return data


@dataclass
class DetectedSegment:
    start: float
    end: float
    kills: int


ProgressCallback = Callable[[str, float | None], None]


class ValorantNetwork:
    def __init__(self, path: Path = NETWORK_PATH) -> None:
        if not path.exists():
            raise FileNotFoundError(f"network weights not found: {path}")
        self.weights = np.load(path, allow_pickle=True)

    @staticmethod
    def _sigmoid(value: np.ndarray) -> np.ndarray:
        value = np.clip(value, -500, 500)
        return 1.0 / (1.0 + np.exp(-value))

    def query(self, inputs: np.ndarray) -> np.ndarray:
        values = np.array(inputs, ndmin=2).T
        for weights in self.weights:
            values = self._sigmoid(np.dot(weights, values))
        return values


def tool_filename(tool: str) -> str:
    return f"{tool}.exe" if os.name == "nt" else tool


def resolve_tool(tool: str) -> str | None:
    bundled_paths = [
        PROJECT_ROOT / "ffmpeg" / tool_filename(tool),
        PROJECT_ROOT / "vendor" / "ffmpeg" / tool_filename(tool),
    ]
    for path in bundled_paths:
        if path.exists():
            return str(path)
    return shutil.which(tool)


def hidden_subprocess_kwargs() -> dict:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if os.name == "nt" and creationflags:
        return {"creationflags": creationflags}
    return {}


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    resolved_command = list(command)
    if resolved_command and resolved_command[0] in {"ffmpeg", "ffprobe", "ffplay"}:
        resolved_command[0] = resolve_tool(resolved_command[0]) or resolved_command[0]
    return subprocess.run(
        resolved_command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **hidden_subprocess_kwargs(),
    )


def require_ffmpeg() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if resolve_tool(tool) is None:
            raise RuntimeError(f"{tool} is not bundled and is not installed on PATH")


def ffprobe_json(path: Path) -> dict:
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(path),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"ffprobe failed for {path}")
    return json.loads(result.stdout)


def get_video_info(path: Path) -> VideoInfo:
    metadata = ffprobe_json(path)
    duration = float(metadata.get("format", {}).get("duration") or 0)
    return VideoInfo(
        path=str(path),
        name=path.name,
        duration=duration,
        size_bytes=path.stat().st_size,
    )


def get_video_size(path: Path) -> tuple[int, int]:
    metadata = ffprobe_json(path)
    for stream in metadata.get("streams", []):
        if stream.get("codec_type") == "video":
            return int(stream["width"]), int(stream["height"])
    raise RuntimeError(f"no video stream found: {path}")


def discover_videos(root: Path, recursive: bool = False) -> list[VideoInfo]:
    require_ffmpeg()
    if not root.exists():
        raise FileNotFoundError(root)

    pattern: Iterable[Path]
    if root.is_file():
        pattern = [root]
    elif recursive:
        pattern = (
            path
            for path in root.rglob("*")
            if not any(part in DEFAULT_EXCLUDES for part in path.parts)
        )
    else:
        pattern = root.iterdir()

    videos: list[VideoInfo] = []
    for path in sorted(pattern):
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            try:
                videos.append(get_video_info(path))
            except Exception:
                continue
    return videos


def preprocess_valorant_frame(frame_path: Path, mask: Image.Image) -> np.ndarray:
    image = Image.open(frame_path).convert("L")
    if image.size != (122, 62):
        image = image.resize((122, 62), Image.Resampling.BICUBIC)

    def apply_filter(source: Image.Image, image_filter: ImageFilter.Filter) -> Image.Image:
        filtered = source.filter(image_filter)
        filtered = filtered.crop((1, 1, filtered.width - 2, filtered.height - 2))
        fitted_mask = mask.crop((0, 0, filtered.width, filtered.height))
        filtered = filtered.convert("RGBA")
        filtered.paste(fitted_mask, (0, 0), fitted_mask)

        left = filtered.crop((0, 0, 25, 60))
        right = filtered.crop((95, 0, 120, 60))

        final = Image.new("RGB", (50, 60))
        final.paste(left.convert("RGB"), (0, 0))
        final.paste(right.convert("RGB"), (25, 0))
        return final.crop((0, 20, 50, 60))

    edges = apply_filter(image, ImageFilter.FIND_EDGES)
    enhanced = apply_filter(image, ImageFilter.EDGE_ENHANCE_MORE).transpose(
        Image.Transpose.FLIP_TOP_BOTTOM
    )

    final = Image.new("RGB", (50, 80))
    final.paste(edges, (0, 0))
    final.paste(enhanced, (0, 40))
    grayscale = ImageOps.grayscale(final)
    values = np.asarray(grayscale, dtype=np.float64).reshape(-1)
    return (values / 255.0 * 0.99) + 0.01


def valorant_crop_filter(width: int, height: int) -> str:
    scale_x = width / 1920
    scale_y = height / 1080
    crop_w = max(20, int(round(122 * scale_x)))
    crop_h = max(20, int(round(62 * scale_y)))
    crop_x = min(max(0, int(round(899 * scale_x))), max(0, width - crop_w))
    crop_y = min(max(0, int(round(801 * scale_y))), max(0, height - crop_h))
    return f"fps={{fps}},crop={crop_w}:{crop_h}:{crop_x}:{crop_y}"


def extract_killfeed_frames(
    video_path: Path,
    frames_dir: Path,
    framerate: int,
    max_seconds: float | None = None,
) -> None:
    width, height = get_video_size(video_path)
    vf = valorant_crop_filter(width, height).format(fps=framerate)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        vf,
    ]
    if max_seconds and max_seconds > 0:
        command.extend(["-t", str(max_seconds)])
    command.extend(["-start_number", "0", str(frames_dir / "%08d.bmp")])
    result = run_command(command)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg frame extraction failed")


def group_kill_frames(
    frame_indexes: list[int],
    framerate: int,
    seconds_before: float,
    seconds_after: float,
    merge_gap_seconds: float,
    min_event_seconds: float = 0.0,
) -> list[tuple[float, float]]:
    return [
        (segment.start, segment.end)
        for segment in group_kill_frame_details(
            frame_indexes,
            framerate=framerate,
            seconds_before=seconds_before,
            seconds_after=seconds_after,
            merge_gap_seconds=merge_gap_seconds,
            min_event_seconds=min_event_seconds,
        )
    ]


def group_kill_frame_details(
    frame_indexes: list[int],
    framerate: int,
    seconds_before: float,
    seconds_after: float,
    merge_gap_seconds: float,
    min_event_seconds: float = 0.0,
) -> list[DetectedSegment]:
    if not frame_indexes:
        return []

    groups: list[list[int]] = []
    current: list[int] = []
    for index in frame_indexes:
        if not current or index - current[-1] == 1:
            current.append(index)
        else:
            groups.append(current)
            current = [index]
    groups.append(current)

    before = int(round(seconds_before * framerate))
    after = int(round(seconds_after * framerate))
    min_frames = max(3, int(math.ceil(min_event_seconds * framerate)))
    ranges: list[tuple[int, int, int]] = []
    for group in groups:
        if len(group) < min_frames:
            continue
        ranges.append((max(0, group[0] - before), group[-1] + after, 1))

    merge_gap = int(round(merge_gap_seconds * framerate))
    merged: list[tuple[int, int, int]] = []
    for start, end, kills in ranges:
        if merged and merged[-1][1] + merge_gap >= start:
            merged[-1] = (
                merged[-1][0],
                max(merged[-1][1], end),
                merged[-1][2] + kills,
            )
        else:
            merged.append((start, end, kills))

    return [
        DetectedSegment(start=start / framerate, end=end / framerate, kills=kills)
        for start, end, kills in merged
    ]


def safe_stem(path: Path) -> str:
    allowed = []
    for char in path.stem:
        if char.isalnum() or char in ("-", "_"):
            allowed.append(char)
        else:
            allowed.append("-")
    return "".join(allowed).strip("-") or "valorant"


def cut_segment(
    video_path: Path,
    output_path: Path,
    start: float,
    end: float,
    copy_streams: bool = False,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-to",
        f"{end:.3f}",
        "-i",
        str(video_path),
    ]
    if copy_streams:
        command.extend(["-c", "copy", "-avoid_negative_ts", "make_zero"])
    else:
        command.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "slow",
                "-crf",
                "14",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "copy",
                "-movflags",
                "+faststart",
            ]
        )
    command.append(str(output_path))
    result = run_command(command)
    if result.returncode != 0 and not copy_streams:
        fallback = list(command)
        for index in range(len(fallback) - 1):
            if fallback[index] == "-c:a" and fallback[index + 1] == "copy":
                fallback[index + 1] = "aac"
                fallback[index + 2:index + 2] = ["-b:a", "192k"]
                result = run_command(fallback)
                break
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"failed to cut {output_path.name}")


def detect_segments(
    video_path: Path,
    confidence: float = 0.8,
    framerate: int = 8,
    seconds_before: float = 4.0,
    seconds_after: float = 0.5,
    merge_gap_seconds: float = 3.0,
    max_seconds: float | None = None,
    strict_own_kills: bool = False,
    min_event_seconds: float = 0.0,
    progress: ProgressCallback | None = None,
) -> list[tuple[float, float]]:
    return [
        (segment.start, segment.end)
        for segment in detect_segment_details(
            video_path=video_path,
            confidence=confidence,
            framerate=framerate,
            seconds_before=seconds_before,
            seconds_after=seconds_after,
            merge_gap_seconds=merge_gap_seconds,
            max_seconds=max_seconds,
            strict_own_kills=strict_own_kills,
            min_event_seconds=min_event_seconds,
            progress=progress,
        )
    ]


def detect_segment_details(
    video_path: Path,
    confidence: float = 0.8,
    framerate: int = 8,
    seconds_before: float = 4.0,
    seconds_after: float = 0.5,
    merge_gap_seconds: float = 3.0,
    max_seconds: float | None = None,
    strict_own_kills: bool = False,
    min_event_seconds: float = 0.0,
    progress: ProgressCallback | None = None,
) -> list[DetectedSegment]:
    require_ffmpeg()
    network = ValorantNetwork()
    mask = Image.open(MASK_PATH).convert("RGBA")
    effective_confidence = max(confidence, 0.94) if strict_own_kills else confidence
    effective_min_event_seconds = (
        max(min_event_seconds, 0.75) if strict_own_kills else min_event_seconds
    )

    with tempfile.TemporaryDirectory(prefix="valorant_frames_") as temp:
        frames_dir = Path(temp)
        if progress:
            progress("正在抽取击杀信息区域帧", 0.05)
        extract_killfeed_frames(video_path, frames_dir, framerate, max_seconds)

        frames = sorted(frames_dir.glob("*.bmp"))
        if progress:
            progress(f"开始识别 {len(frames)} 帧", 0.15)

        kill_frames: list[int] = []
        total = max(1, len(frames))
        for i, frame in enumerate(frames):
            inputs = preprocess_valorant_frame(frame, mask)
            output = network.query(inputs)
            if float(output.reshape(-1)[1]) >= effective_confidence:
                kill_frames.append(i)
            if progress and (i % 100 == 0 or i == total - 1):
                progress(f"已分析 {i + 1}/{total} 帧", 0.15 + 0.65 * ((i + 1) / total))

    return group_kill_frame_details(
        kill_frames,
        framerate=framerate,
        seconds_before=seconds_before,
        seconds_after=seconds_after,
        merge_gap_seconds=merge_gap_seconds,
        min_event_seconds=effective_min_event_seconds,
    )


def process_video(
    video_path: Path,
    output_dir: Path,
    confidence: float = 0.8,
    framerate: int = 8,
    seconds_before: float = 4.0,
    seconds_after: float = 0.5,
    merge_gap_seconds: float = 3.0,
    max_seconds: float | None = None,
    strict_own_kills: bool = False,
    min_event_seconds: float = 0.0,
    copy_streams: bool = False,
    progress: ProgressCallback | None = None,
) -> list[ClipSegment]:
    video_path = video_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(video_path)

    if progress:
        progress(f"载入视频: {video_path.name}", 0.0)

    ranges = detect_segment_details(
        video_path=video_path,
        confidence=confidence,
        framerate=framerate,
        seconds_before=seconds_before,
        seconds_after=seconds_after,
        merge_gap_seconds=merge_gap_seconds,
        max_seconds=max_seconds,
        strict_own_kills=strict_own_kills,
        min_event_seconds=min_event_seconds,
        progress=progress,
    )

    if progress:
        progress(f"检测到 {len(ranges)} 个片段，开始导出", 0.82)

    target_dir = output_dir / safe_stem(video_path)
    clips: list[ClipSegment] = []
    for index, segment in enumerate(ranges, start=1):
        start, end = segment.start, segment.end
        if end <= start or math.isclose(end, start):
            continue
        name = f"{index:03d}_{start:.3f}-{end:.3f}.mp4"
        path = target_dir / name
        cut_segment(video_path, path, start, end, copy_streams=copy_streams)
        clips.append(
            ClipSegment(
                start=start,
                end=end,
                path=str(path),
                name=name,
                kills=segment.kills,
            )
        )
        if progress:
            progress(f"已导出 {index}/{len(ranges)}: {name}", 0.82 + 0.16 * (index / max(1, len(ranges))))

    if progress:
        progress("完成", 1.0)
    return clips
