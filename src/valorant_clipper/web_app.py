from __future__ import annotations

import os
import sys
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .core import DEFAULT_OUTPUT_DIR, DEFAULT_SOURCE_DIR, discover_videos, process_video
from .paths import resource_root


PROJECT_ROOT = resource_root()
STATIC_DIR = PROJECT_ROOT / "static" / "valorant_clipper"

app = FastAPI(title="Valorant Highlight Clipper")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

jobs: dict[str, dict[str, Any]] = {}
jobs_lock = threading.Lock()


class JobRequest(BaseModel):
    input_path: str
    output_dir: str = str(DEFAULT_OUTPUT_DIR)
    confidence: float = Field(0.8, ge=0.01, le=0.99)
    framerate: int = Field(8, ge=1, le=30)
    seconds_before: float = Field(4.0, ge=0, le=30)
    seconds_after: float = Field(0.5, ge=0, le=30)
    merge_gap_seconds: float = Field(3.0, ge=0, le=60)
    max_seconds: float | None = Field(None, ge=1)
    strict_own_kills: bool = True
    min_event_seconds: float = Field(0.45, ge=0, le=2)
    copy_streams: bool = False


class PathChoiceRequest(BaseModel):
    kind: str = Field(pattern="^(file|folder)$")
    prompt: str = "选择路径"


def file_payload(path: str) -> dict[str, Any]:
    file_path = Path(path)
    return {
        "path": str(file_path),
        "url": f"/api/file?path={quote(str(file_path))}",
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/defaults")
def defaults() -> dict[str, str]:
    return {
        "source_dir": str(DEFAULT_SOURCE_DIR),
        "output_dir": str(DEFAULT_OUTPUT_DIR),
    }


@app.post("/api/choose-path")
def choose_path(request: PathChoiceRequest) -> dict[str, str]:
    if os.name == "nt":
        return choose_windows_path(request)

    if request.kind == "file":
        script = (
            f'set chosenPath to choose file with prompt "{request.prompt}"\n'
            "POSIX path of chosenPath"
        )
    else:
        script = (
            f'set chosenPath to choose folder with prompt "{request.prompt}"\n'
            "POSIX path of chosenPath"
        )

    result = subprocess.run(
        ["osascript", "-e", script],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=400, detail=result.stderr.strip() or "已取消选择")
    return {"path": result.stdout.strip()}


def choose_windows_path(request: PathChoiceRequest) -> dict[str, str]:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if request.kind == "file":
            path = filedialog.askopenfilename(
                title=request.prompt,
                filetypes=[
                    ("Video files", "*.mp4 *.mov *.mkv *.avi *.m4v *.flv"),
                    ("All files", "*.*"),
                ],
            )
        else:
            path = filedialog.askdirectory(title=request.prompt)
    finally:
        root.destroy()

    if not path:
        raise HTTPException(status_code=400, detail="已取消选择")
    return {"path": str(Path(path))}


@app.get("/api/videos")
def videos(root: str = str(DEFAULT_SOURCE_DIR), recursive: bool = False) -> list[dict[str, Any]]:
    try:
        return [video.__dict__ for video in discover_videos(Path(root), recursive=recursive)]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/jobs")
def create_job(request: JobRequest) -> dict[str, str]:
    job_id = str(uuid.uuid4())
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "progress": 0,
            "message": "等待开始",
            "logs": [],
            "segments": [],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

    def update(message: str, progress: float | None = None) -> None:
        with jobs_lock:
            job = jobs[job_id]
            job["message"] = message
            if progress is not None:
                job["progress"] = max(0, min(1, progress))
            job["logs"].append(f"{datetime.now().strftime('%H:%M:%S')}  {message}")
            job["logs"] = job["logs"][-200:]

    def worker() -> None:
        with jobs_lock:
            jobs[job_id]["status"] = "running"
        try:
            clips = process_video(
                video_path=Path(request.input_path),
                output_dir=Path(request.output_dir),
                confidence=request.confidence,
                framerate=request.framerate,
                seconds_before=request.seconds_before,
                seconds_after=request.seconds_after,
                merge_gap_seconds=request.merge_gap_seconds,
                max_seconds=request.max_seconds,
                strict_own_kills=request.strict_own_kills,
                min_event_seconds=request.min_event_seconds,
                copy_streams=request.copy_streams,
                progress=update,
            )
            with jobs_lock:
                jobs[job_id]["status"] = "done"
                jobs[job_id]["progress"] = 1
                jobs[job_id]["message"] = f"完成，导出 {len(clips)} 个片段"
                jobs[job_id]["segments"] = [
                    {**clip.to_dict(), **file_payload(clip.path)} for clip in clips
                ]
        except Exception as exc:
            with jobs_lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["message"] = str(exc)
                jobs[job_id]["logs"].append(f"{datetime.now().strftime('%H:%M:%S')}  错误: {exc}")

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return {"id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with jobs_lock:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return dict(job)


@app.get("/api/file")
def local_file(path: str) -> FileResponse:
    file_path = Path(path).expanduser().resolve()
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(file_path)


@app.post("/api/open-folder")
def open_folder(path: str) -> dict[str, str]:
    folder = Path(path).expanduser().resolve()
    if folder.is_file():
        folder = folder.parent
    if not folder.exists():
        raise HTTPException(status_code=404, detail="folder not found")
    if os.name == "nt":
        os.startfile(str(folder))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(folder)])
    else:
        subprocess.Popen(["xdg-open", str(folder)])
    return {"status": "ok"}
