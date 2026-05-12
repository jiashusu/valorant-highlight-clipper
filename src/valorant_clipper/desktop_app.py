from __future__ import annotations

import os
import queue
import hashlib
import subprocess
import sys
import threading
import tempfile
import webbrowser
from pathlib import Path
from tkinter import BooleanVar, DoubleVar, IntVar, StringVar, Tk, filedialog, messagebox
from tkinter import ttk

from PIL import Image, ImageDraw, ImageTk

from .core import (
    ClipSegment,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_DIR,
    discover_videos,
    hidden_subprocess_kwargs,
    process_video,
    resolve_tool,
)
from .update_checker import UpdateResult, check_for_update


APP_TITLE = "Valorant 高光剪辑"
UPDATE_CHECK_INTERVAL_MS = 30 * 60 * 1000
THUMBNAIL_WIDTH = 384
THUMBNAIL_HEIGHT = 216
CLIP_CARD_COLUMNS = 3
CARD_PREVIEW_FPS = 30
UI_FONT = ("Helvetica", 12)
UI_FONT_BOLD = ("Helvetica", 12, "bold")
TITLE_FONT = ("Helvetica", 22, "bold")
MONO_FONT = ("Menlo", 11)
COLORS = {
    "bg": "#07090f",
    "panel": "#10141d",
    "panel_alt": "#151b26",
    "card": "#111827",
    "card_hover": "#152033",
    "field": "#0b1020",
    "border": "#273244",
    "text": "#e7ecf5",
    "muted": "#94a3b8",
    "accent": "#22d3ee",
    "accent_hover": "#38bdf8",
    "danger": "#ef4444",
    "danger_soft": "#3f1d25",
    "warning": "#facc15",
    "warning_bg": "#1f1a0b",
    "select": "#0e7490",
    "progress": "#10b981",
}


def open_path(path: Path) -> None:
    path = path.expanduser().resolve(strict=False)
    if os.name == "nt":
        if path.is_file():
            subprocess.Popen(["explorer.exe", f'/select,"{path}"'], **hidden_subprocess_kwargs())
        elif path.exists():
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            raise FileNotFoundError(path)
    elif sys.platform == "darwin":
        if path.is_file():
            subprocess.Popen(["open", "-R", str(path)])
        else:
            subprocess.Popen(["open", str(path)])
    else:
        if path.is_file():
            path = path.parent
        subprocess.Popen(["xdg-open", str(path)])


def reveal_exported_clip(path: Path) -> None:
    path = path.expanduser().resolve(strict=False)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(path)
    open_path(path)


class DesktopApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("1720x980")
        self.root.minsize(1360, 840)
        self.root.configure(bg=COLORS["bg"])

        self.source_path = StringVar(value=str(DEFAULT_SOURCE_DIR))
        self.output_dir = StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.confidence = DoubleVar(value=0.93)
        self.framerate = IntVar(value=8)
        self.seconds_before = DoubleVar(value=4.0)
        self.seconds_after = DoubleVar(value=0.5)
        self.merge_gap = DoubleVar(value=3.0)
        self.max_seconds = StringVar(value="")
        self.strict_own_kills = BooleanVar(value=True)
        self.min_event_seconds = DoubleVar(value=0.75)
        self.copy_streams = BooleanVar(value=False)
        self.recursive = BooleanVar(value=False)
        self.status = StringVar(value="准备就绪")

        self.videos: list[dict[str, object]] = []
        self.clips: list[ClipSegment] = []
        self.selected_video: Path | None = None
        self.selected_clip: ClipSegment | None = None
        self.worker_thread: threading.Thread | None = None
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.last_update_prompt_sha: str | None = None
        self.player_process: subprocess.Popen[str] | None = None
        self.selected_clip_index: int | None = None
        self.playing_clip_index: int | None = None
        self.playing_mode: str | None = None
        self.preview_play_token = 0
        self.thumbnail_cache_dir = Path(tempfile.gettempdir()) / "valorant_clipper_thumbnails"
        self.card_preview_cache_dir = Path(tempfile.gettempdir()) / "valorant_clipper_card_previews"
        self.thumbnail_generation = 0
        self.thumbnail_photos: dict[int, ImageTk.PhotoImage] = {}
        self.thumbnail_labels: dict[int, ttk.Label] = {}
        self.play_buttons: dict[int, ttk.Button] = {}
        self.card_preview_images: list[ImageTk.PhotoImage] = []
        self.card_preview_frame_index = 0
        self.card_preview_after_id: str | None = None

        self._setup_style()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self._drain_events)
        self.root.after(1500, lambda: self.check_for_updates(manual=False))

    def _setup_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        self.root.option_add("*Font", UI_FONT)
        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], font=UI_FONT)
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"])
        style.configure("Header.TFrame", background=COLORS["bg"])
        style.configure("Actions.TFrame", background=COLORS["card"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=UI_FONT)
        style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"])
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=TITLE_FONT)
        style.configure("Warning.TLabel", background=COLORS["warning_bg"], foreground=COLORS["warning"])
        style.configure("Card.TFrame", background=COLORS["card"], relief="flat")
        style.configure("Card.TLabel", background=COLORS["card"], foreground=COLORS["text"])
        style.configure("CardMuted.TLabel", background=COLORS["card"], foreground=COLORS["muted"])
        style.configure(
            "TLabelframe",
            background=COLORS["panel"],
            foreground=COLORS["text"],
            bordercolor=COLORS["border"],
            relief="flat",
            borderwidth=0,
        )
        style.configure("TLabelframe.Label", background=COLORS["panel"], foreground=COLORS["text"], font=UI_FONT_BOLD)
        style.configure(
            "TEntry",
            fieldbackground=COLORS["field"],
            foreground=COLORS["text"],
            insertcolor=COLORS["text"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["border"],
            darkcolor=COLORS["border"],
        )
        style.configure(
            "TButton",
            background=COLORS["panel_alt"],
            foreground=COLORS["text"],
            bordercolor=COLORS["border"],
            focusthickness=1,
            focuscolor=COLORS["accent"],
            padding=(12, 7),
        )
        style.map("TButton", background=[("active", "#1f2937"), ("pressed", "#0f172a")])
        style.configure("Accent.TButton", background=COLORS["accent"], foreground="#041016")
        style.map("Accent.TButton", background=[("active", COLORS["accent_hover"]), ("pressed", "#0891b2")])
        style.configure("Danger.TButton", background=COLORS["danger_soft"], foreground="#fecdd3")
        style.map("Danger.TButton", background=[("active", COLORS["danger"]), ("pressed", "#991b1b")])
        style.configure("TCheckbutton", background=COLORS["panel"], foreground=COLORS["text"])
        style.map("TCheckbutton", background=[("active", COLORS["panel"])])
        style.configure(
            "Treeview",
            background=COLORS["field"],
            fieldbackground=COLORS["field"],
            foreground=COLORS["text"],
            bordercolor=COLORS["border"],
            rowheight=28,
        )
        style.configure("Treeview.Heading", background=COLORS["panel_alt"], foreground=COLORS["text"], font=UI_FONT_BOLD)
        style.map("Treeview", background=[("selected", COLORS["select"])], foreground=[("selected", COLORS["text"])])
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=COLORS["panel_alt"],
            background=COLORS["progress"],
            bordercolor=COLORS["border"],
            lightcolor=COLORS["progress"],
            darkcolor=COLORS["progress"],
        )
        for orient in ("Vertical", "Horizontal"):
            style.configure(
                f"{orient}.TScrollbar",
                background=COLORS["panel_alt"],
                troughcolor=COLORS["field"],
                bordercolor=COLORS["border"],
                arrowcolor=COLORS["muted"],
                lightcolor=COLORS["panel_alt"],
                darkcolor=COLORS["panel_alt"],
            )

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(18, 14, 18, 10), style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text=APP_TITLE, style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.status, style="Muted.TLabel").grid(row=0, column=1, sticky="e")
        ttk.Button(header, text="检查更新", command=lambda: self.check_for_updates(manual=True)).grid(
            row=0, column=2, sticky="e", padx=(10, 0)
        )

        body = ttk.PanedWindow(self.root, orient="horizontal")
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))

        left = ttk.Frame(body, padding=12, style="Panel.TFrame")
        right = ttk.Frame(body, padding=12, style="Panel.TFrame")
        body.add(left, weight=2)
        body.add(right, weight=6)

        self._build_left_panel(left)
        self._build_right_panel(right)

        footer = ttk.Frame(self.root, padding=(18, 0, 18, 16))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(footer, mode="determinate", maximum=100)
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.start_button = ttk.Button(footer, text="开始剪辑", command=self.start_job, style="Accent.TButton")
        self.start_button.grid(row=0, column=1)

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(5, weight=1)

        paths = ttk.LabelFrame(parent, text="路径", padding=10)
        paths.grid(row=0, column=0, sticky="ew")
        paths.columnconfigure(0, weight=1)

        ttk.Label(paths, text="素材文件夹或视频文件").grid(row=0, column=0, sticky="w")
        ttk.Entry(paths, textvariable=self.source_path).grid(row=1, column=0, sticky="ew", pady=(4, 6))
        path_buttons = ttk.Frame(paths)
        path_buttons.grid(row=2, column=0, sticky="ew")
        ttk.Button(path_buttons, text="选择文件夹", command=self.choose_source_folder).pack(side="left")
        ttk.Button(path_buttons, text="选择视频", command=self.choose_source_file).pack(side="left", padx=6)
        ttk.Checkbutton(path_buttons, text="递归扫描", variable=self.recursive).pack(side="left", padx=6)

        ttk.Label(paths, text="输出目录").grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(paths, textvariable=self.output_dir).grid(row=4, column=0, sticky="ew", pady=(4, 6))
        output_buttons = ttk.Frame(paths)
        output_buttons.grid(row=5, column=0, sticky="ew")
        ttk.Button(output_buttons, text="选择输出目录", command=self.choose_output_dir).pack(side="left")
        ttk.Button(output_buttons, text="打开输出目录", command=self.open_output_dir).pack(side="left", padx=6)

        settings = ttk.LabelFrame(parent, text="参数", padding=10)
        settings.grid(row=1, column=0, sticky="ew", pady=10)
        for col in range(4):
            settings.columnconfigure(col, weight=1)

        self._number(settings, "置信度", self.confidence, 0, 0)
        self._number(settings, "识别帧率", self.framerate, 0, 2)
        self._number(settings, "提前秒数", self.seconds_before, 1, 0)
        self._number(settings, "延后秒数", self.seconds_after, 1, 2)
        self._number(settings, "合并间隔", self.merge_gap, 2, 0)
        self._number(settings, "最短事件秒", self.min_event_seconds, 2, 2)

        ttk.Label(settings, text="最多分析秒数").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(settings, textvariable=self.max_seconds, width=10).grid(row=3, column=1, sticky="ew", pady=(8, 0))
        ttk.Checkbutton(settings, text="严格过滤队友击杀（推荐）", variable=self.strict_own_kills).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        ttk.Checkbutton(settings, text="快速无损截取", variable=self.copy_streams).grid(
            row=4, column=2, columnspan=2, sticky="w", pady=(10, 0)
        )

        scan_bar = ttk.Frame(parent)
        scan_bar.grid(row=2, column=0, sticky="ew")
        ttk.Button(scan_bar, text="扫描视频", command=self.scan_videos).pack(side="left")
        ttk.Button(scan_bar, text="清空日志", command=self.clear_log).pack(
            side="left", padx=6
        )

        video_frame = ttk.LabelFrame(parent, text="视频", padding=8)
        video_frame.grid(row=5, column=0, sticky="nsew", pady=(10, 0))
        video_frame.columnconfigure(0, weight=1)
        video_frame.rowconfigure(0, weight=1)
        self.video_list = ttk.Treeview(
            video_frame,
            columns=("duration", "size", "path"),
            show="headings",
            selectmode="browse",
        )
        self.video_list.heading("duration", text="时长")
        self.video_list.heading("size", text="大小")
        self.video_list.heading("path", text="路径")
        self.video_list.column("duration", width=70, anchor="center", stretch=False)
        self.video_list.column("size", width=80, anchor="center", stretch=False)
        self.video_list.column("path", width=320)
        self.video_list.grid(row=0, column=0, sticky="nsew")
        self.video_list.bind("<<TreeviewSelect>>", self._select_video)
        video_scrollbar = ttk.Scrollbar(video_frame, orient="vertical", command=self.video_list.yview)
        video_scrollbar.grid(row=0, column=1, sticky="ns")
        self.video_list.configure(yscrollcommand=video_scrollbar.set)

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        parent.rowconfigure(4, weight=3)

        ttk.Label(parent, text="处理日志").grid(row=0, column=0, sticky="w")
        self.log_box = self._text(parent, row=1)

        results_header = ttk.Frame(parent)
        results_header.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        results_header.columnconfigure(1, weight=1)
        ttk.Label(results_header, text="Highlights").grid(row=0, column=0, sticky="w")
        ttk.Label(results_header, text="低清预览 / 高清播放").grid(row=0, column=1, sticky="e")

        ttk.Label(
            parent,
            text="提示：当前版本仍可能输出队友击杀片段，可先手动删除；后续会继续更新识别逻辑。",
            anchor="w",
            padding=(10, 7),
            style="Warning.TLabel",
        ).grid(row=3, column=0, sticky="ew", pady=(6, 0))

        clips_frame = ttk.Frame(parent)
        clips_frame.grid(row=4, column=0, sticky="nsew", pady=(8, 0))
        clips_frame.columnconfigure(0, weight=1)
        clips_frame.rowconfigure(0, weight=1)

        import tkinter as tk

        self.clips_canvas = tk.Canvas(clips_frame, highlightthickness=0, bg=COLORS["panel"], bd=0)
        self.clips_canvas.grid(row=0, column=0, sticky="nsew")
        clip_scrollbar = ttk.Scrollbar(clips_frame, orient="vertical", command=self.clips_canvas.yview)
        clip_scrollbar.grid(row=0, column=1, sticky="ns")
        self.clips_canvas.configure(yscrollcommand=clip_scrollbar.set)

        self.clips_container = ttk.Frame(self.clips_canvas)
        self.clips_window = self.clips_canvas.create_window((0, 0), window=self.clips_container, anchor="nw")
        self.clips_container.bind(
            "<Configure>",
            lambda _event: self.clips_canvas.configure(scrollregion=self.clips_canvas.bbox("all")),
        )
        self.clips_canvas.bind(
            "<Configure>",
            lambda event: self.clips_canvas.itemconfigure(self.clips_window, width=event.width),
        )

        self.empty_clips_label = ttk.Label(
            self.clips_container,
            text="剪辑完成后会在这里显示低清预览和操作按钮",
            anchor="center",
            style="Muted.TLabel",
        )
        self.empty_clips_label.grid(row=0, column=0, sticky="ew", pady=24)
        self._bind_widget_mousewheel(self.empty_clips_label)
        self._bind_highlights_mousewheel()

    def _number(self, parent: ttk.Frame, label: str, variable: StringVar | DoubleVar | IntVar, row: int, col: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", pady=(8, 0))
        ttk.Entry(parent, textvariable=variable, width=10).grid(row=row, column=col + 1, sticky="ew", pady=(8, 0))

    def _bind_highlights_mousewheel(self) -> None:
        self._bind_widget_mousewheel(self.clips_canvas)
        self._bind_widget_mousewheel(self.clips_container)

    def _bind_widget_mousewheel(self, widget) -> None:
        widget.bind("<MouseWheel>", self._on_highlights_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_highlights_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_highlights_mousewheel, add="+")

    def _on_highlights_mousewheel(self, event) -> str:
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.clips_canvas.yview_scroll(delta, "units")
        return "break"

    def _text(self, parent: ttk.Frame, row: int):
        frame = ttk.Frame(parent, style="Panel.TFrame")
        frame.grid(row=row, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        import tkinter as tk

        text = tk.Text(
            frame,
            height=8,
            wrap="word",
            bg=COLORS["field"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["select"],
            selectforeground=COLORS["text"],
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
            font=MONO_FONT,
            state="disabled",
        )
        text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scrollbar.set)
        return text

    def append_log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def clear_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def choose_source_folder(self) -> None:
        path = filedialog.askdirectory(title="选择素材文件夹")
        if path:
            self.source_path.set(path)
            self.scan_videos()

    def choose_source_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 Valorant 视频",
            filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi *.m4v *.flv"), ("All files", "*.*")],
        )
        if path:
            self.source_path.set(path)
            self.scan_videos()

    def choose_output_dir(self) -> None:
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir.set(path)

    def open_output_dir(self) -> None:
        open_path(Path(self.output_dir.get()))

    def scan_videos(self) -> None:
        self.status.set("扫描中")
        self._run_thread(self._scan_worker)

    def check_for_updates(self, manual: bool = True) -> None:
        if manual:
            self.status.set("检查更新中")
        thread = threading.Thread(target=self._update_worker, args=(manual,), daemon=True)
        thread.start()

    def _update_worker(self, manual: bool) -> None:
        try:
            result = check_for_update()
            self.events.put(("update", (manual, result)))
        except Exception as exc:
            self.events.put(("update_error", (manual, str(exc))))

    def _scan_worker(self) -> None:
        try:
            videos = discover_videos(Path(self.source_path.get()), recursive=self.recursive.get())
            self.events.put(("videos", videos))
        except Exception as exc:
            self.events.put(("error", f"扫描失败: {exc}"))

    def _select_video(self, _event: object | None = None) -> None:
        selection = self.video_list.selection()
        if not selection:
            self.selected_video = None
            return
        item = self.video_list.item(selection[0])
        values = item.get("values", [])
        self.selected_video = Path(values[2]) if len(values) >= 3 else None

    def _run_thread(self, target) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning(APP_TITLE, "当前还有任务在运行。")
            return
        self.worker_thread = threading.Thread(target=target, daemon=True)
        self.worker_thread.start()

    def start_job(self) -> None:
        if not self.selected_video:
            self._select_first_video_if_available()
        if not self.selected_video:
            messagebox.showwarning(APP_TITLE, "请先扫描并选择一个视频。")
            return
        self.stop_preview()
        self.clips = []
        self.selected_clip = None
        self.selected_clip_index = None
        self.clear_clip_cards()
        self.start_button.configure(state="disabled")
        self.progress.configure(value=0)
        self.status.set("剪辑中")
        self._run_thread(self._job_worker)

    def _job_worker(self) -> None:
        assert self.selected_video is not None
        try:
            max_seconds_text = self.max_seconds.get().strip()
            max_seconds = float(max_seconds_text) if max_seconds_text else None

            def progress(message: str, value: float | None = None) -> None:
                self.events.put(("log", message))
                if value is not None:
                    self.events.put(("progress", value))

            clips = process_video(
                video_path=self.selected_video,
                output_dir=Path(self.output_dir.get()),
                confidence=float(self.confidence.get()),
                framerate=int(self.framerate.get()),
                seconds_before=float(self.seconds_before.get()),
                seconds_after=float(self.seconds_after.get()),
                merge_gap_seconds=float(self.merge_gap.get()),
                max_seconds=max_seconds,
                strict_own_kills=bool(self.strict_own_kills.get()),
                min_event_seconds=float(self.min_event_seconds.get()),
                copy_streams=bool(self.copy_streams.get()),
                progress=progress,
            )
            self.events.put(("clips", clips))
        except Exception as exc:
            self.events.put(("error", f"剪辑失败: {exc}"))
        finally:
            self.events.put(("done", None))

    def _drain_events(self) -> None:
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "videos":
                self._render_videos(payload)  # type: ignore[arg-type]
            elif kind == "log":
                self.append_log(f"{payload}\n")
            elif kind == "progress":
                self.progress.configure(value=int(float(payload) * 100))
            elif kind == "clips":
                self._render_clips(payload)  # type: ignore[arg-type]
            elif kind == "error":
                self.status.set("出错")
                self.append_log(f"{payload}\n")
                messagebox.showerror(APP_TITLE, str(payload))
            elif kind == "update":
                manual, result = payload  # type: ignore[misc]
                self._handle_update_result(bool(manual), result)  # type: ignore[arg-type]
            elif kind == "update_error":
                manual, message = payload  # type: ignore[misc]
                self._handle_update_error(bool(manual), str(message))
            elif kind == "thumbnail_ready":
                generation, index, image_path = payload  # type: ignore[misc]
                self._handle_thumbnail_ready(int(generation), int(index), Path(str(image_path)))
            elif kind == "thumbnail_error":
                generation, index = payload  # type: ignore[misc]
                self._handle_thumbnail_error(int(generation), int(index))
            elif kind == "card_preview_ready":
                token, index, frames = payload  # type: ignore[misc]
                self._handle_card_preview_ready(int(token), int(index), frames)  # type: ignore[arg-type]
            elif kind == "card_preview_error":
                token, message = payload  # type: ignore[misc]
                self._handle_card_preview_error(int(token), str(message))
            elif kind == "done":
                self.start_button.configure(state="normal")
                if self.status.get() != "出错":
                    self.status.set("完成")
        self.root.after(100, self._drain_events)

    def _handle_update_result(self, manual: bool, result: UpdateResult) -> None:
        if result.update_available:
            if not manual and result.remote_sha == self.last_update_prompt_sha:
                self._schedule_next_update_check()
                return
            self.last_update_prompt_sha = result.remote_sha
            self.status.set(f"有新版本: {result.remote_short}")
            should_open = messagebox.askyesno(
                APP_TITLE,
                f"{result.message}\n\n是否打开 GitHub Actions 下载新版 macOS App？",
            )
            if should_open:
                webbrowser.open(result.download_url)
            if not manual:
                self._schedule_next_update_check()
            return

        if manual:
            self.status.set("已是最新版本")
            messagebox.showinfo(APP_TITLE, result.message)
        elif self.status.get() == "检查更新中":
            self.status.set("准备就绪")
        if not manual:
            self._schedule_next_update_check()

    def _handle_update_error(self, manual: bool, message: str) -> None:
        if manual:
            self.status.set("检查更新失败")
            messagebox.showwarning(APP_TITLE, message)
        elif self.status.get() == "检查更新中":
            self.status.set("准备就绪")
        if not manual:
            self._schedule_next_update_check()

    def _schedule_next_update_check(self) -> None:
        self.root.after(UPDATE_CHECK_INTERVAL_MS, lambda: self.check_for_updates(manual=False))

    def _render_videos(self, videos) -> None:
        self.videos = [video.__dict__ for video in videos]
        self.video_list.delete(*self.video_list.get_children())
        self.selected_video = None
        for index, video in enumerate(self.videos):
            self.video_list.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    self._format_seconds(float(video["duration"])),
                    self._format_size(int(video["size_bytes"])),
                    video["path"],
                ),
            )
        self._select_first_video_if_available()
        self.status.set(f"扫描完成: {len(self.videos)} 个视频")

    def _select_first_video_if_available(self) -> None:
        children = self.video_list.get_children()
        if not children:
            self.selected_video = None
            return
        first = children[0]
        self.video_list.selection_set(first)
        self.video_list.focus(first)
        self.video_list.see(first)
        self._select_video(None)

    def _render_clips(self, clips) -> None:
        self.clips = list(clips)
        self.refresh_clip_cards()
        self.append_log(f"完成，导出 {len(clips)} 个片段\n")
        if self.clips:
            self.select_clip(0)

    def clear_clip_cards(self) -> None:
        self.thumbnail_generation += 1
        self.thumbnail_photos = {}
        self.thumbnail_labels = {}
        self.play_buttons = {}
        for child in self.clips_container.winfo_children():
            child.destroy()
        self.empty_clips_label = ttk.Label(
            self.clips_container,
            text="剪辑完成后会在这里显示低清预览和操作按钮",
            anchor="center",
            style="Muted.TLabel",
        )
        self.empty_clips_label.grid(row=0, column=0, sticky="ew", pady=24)
        self._bind_widget_mousewheel(self.empty_clips_label)

    def refresh_clip_cards(self) -> None:
        self.thumbnail_generation += 1
        generation = self.thumbnail_generation
        self.thumbnail_photos = {}
        self.thumbnail_labels = {}
        self.play_buttons = {}
        for child in self.clips_container.winfo_children():
            child.destroy()
        for column in range(CLIP_CARD_COLUMNS):
            self.clips_container.columnconfigure(column, weight=1, uniform="clip_cards")
        self.selected_clip_index = None
        if not self.clips:
            self.empty_clips_label = ttk.Label(
                self.clips_container,
                text="没有导出片段",
                anchor="center",
                style="Muted.TLabel",
            )
            self.empty_clips_label.grid(row=0, column=0, sticky="ew", pady=24)
            self._bind_widget_mousewheel(self.empty_clips_label)
            return

        for index, clip in enumerate(self.clips):
            self.render_clip_card(index, clip)
            seek_seconds = self.thumbnail_seek_seconds(clip)
            thread = threading.Thread(
                target=self._thumbnail_worker,
                args=(generation, index, clip, seek_seconds),
                daemon=True,
            )
            thread.start()

    def render_clip_card(self, index: int, clip: ClipSegment) -> None:
        row = index // CLIP_CARD_COLUMNS
        column = index % CLIP_CARD_COLUMNS
        card = ttk.Frame(self.clips_container, padding=10, style="Card.TFrame")
        card.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
        card.columnconfigure(0, weight=1)
        self._bind_widget_mousewheel(card)

        preview = ttk.Label(
            card,
            text="生成低清预览中",
            anchor="center",
            style="CardMuted.TLabel",
            width=34,
        )
        preview.grid(row=0, column=0, sticky="ew")
        preview.bind("<Button-1>", lambda _event, i=index: self.play_low_quality_preview(i))
        preview.bind("<Double-1>", lambda _event, i=index: self.play_low_quality_preview(i))
        self._bind_widget_mousewheel(preview)
        self.thumbnail_labels[index] = preview

        title = ttk.Label(
            card,
            text=f"Highlight #{index + 1:03d}",
            font=("Helvetica", 13, "bold"),
            anchor="w",
            style="Card.TLabel",
        )
        title.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        title.bind("<Button-1>", lambda _event, i=index: self.select_clip(i))
        self._bind_widget_mousewheel(title)

        info = ttk.Label(
            card,
            text=(
                f"约 {clip.kills} 杀  ·  {clip.duration:.2f}s\n"
                f"{clip.start:.2f}s - {clip.end:.2f}s"
            ),
            anchor="w",
            justify="left",
            style="CardMuted.TLabel",
        )
        info.grid(row=2, column=0, sticky="ew", pady=(2, 0))
        info.bind("<Button-1>", lambda _event, i=index: self.select_clip(i))
        self._bind_widget_mousewheel(info)

        actions = ttk.Frame(card, style="Actions.TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.columnconfigure(2, weight=1)
        play_button = ttk.Button(
            actions,
            text="高清播放",
            style="Accent.TButton",
            command=lambda i=index: self.play_high_quality(i),
        )
        play_button.grid(row=0, column=0, sticky="ew")
        ttk.Button(actions, text="定位此视频", command=lambda i=index: self.open_selected_clip(i)).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )
        ttk.Button(actions, text="删除", style="Danger.TButton", command=lambda i=index: self.delete_selected_clip(i)).grid(
            row=0, column=2, sticky="ew", padx=(6, 0)
        )
        self._bind_widget_mousewheel(actions)
        self.play_buttons[index] = play_button

    def open_selected_clip(self, index: int | None = None) -> None:
        clip = self.current_clip(index)
        if clip is None:
            return
        clip_path = Path(clip.path).expanduser().resolve(strict=False)
        try:
            reveal_exported_clip(clip_path)
        except Exception as exc:
            self.append_log(f"找不到导出视频：\n{clip_path}\n{exc}\n")
            messagebox.showerror(APP_TITLE, f"找不到导出视频：\n{clip_path}")

    def select_clip(self, index: int | None = None) -> None:
        clip = self.current_clip(index)
        if clip is None:
            self.selected_clip = None
            self.selected_clip_index = None
            return
        self.selected_clip = clip
        self.selected_clip_index = index

    def current_clip(self, index: int | None = None) -> ClipSegment | None:
        if index is None:
            index = self.selected_clip_index
        if index is None:
            return None
        if index < 0 or index >= len(self.clips):
            return None
        return self.clips[index]

    def play_low_quality_preview(self, index: int | None = None) -> None:
        if index is None:
            index = self.selected_clip_index
        if index is None:
            return
        if self.playing_clip_index == index and self.playing_mode == "card":
            self.stop_preview()
            return
        if self.player_process and self.player_process.poll() is None:
            self.stop_preview()
        clip = self.current_clip(index)
        if clip is None:
            return
        self.stop_card_preview(reset_image=True)
        self.select_clip(index)
        self.preview_play_token += 1
        token = self.preview_play_token
        self.playing_clip_index = index
        self.playing_mode = "card"
        self.status.set(f"准备卡片预览: Highlight #{index + 1:03d}")
        label = self.thumbnail_labels.get(index)
        if label is not None:
            label.configure(text="载入预览中")
        thread = threading.Thread(target=self._card_preview_worker, args=(token, index, clip), daemon=True)
        thread.start()

    def _card_preview_worker(self, token: int, index: int, clip: ClipSegment) -> None:
        try:
            frames = self.card_preview_frames_for(clip)
            self.events.put(("card_preview_ready", (token, index, frames)))
        except Exception as exc:
            self.events.put(("card_preview_error", (token, str(exc))))

    def _handle_card_preview_ready(self, token: int, index: int, frames: list[Path]) -> None:
        if token != self.preview_play_token:
            return
        if self.playing_clip_index != index or self.playing_mode != "card":
            return
        try:
            self.card_preview_images = self.load_card_preview_images(frames)
        except Exception as exc:
            self._handle_card_preview_error(token, str(exc))
            return
        self.card_preview_frame_index = 0
        self.status.set(f"卡片内预览: Highlight #{index + 1:03d}")
        self.advance_card_preview()

    def _handle_card_preview_error(self, token: int, message: str) -> None:
        if token != self.preview_play_token:
            return
        self.stop_card_preview()
        self.status.set("卡片预览失败")
        messagebox.showerror(APP_TITLE, f"卡片预览生成失败: {message}")

    def play_high_quality(self, index: int | None = None) -> None:
        if index is None:
            index = self.selected_clip_index
        if index is None:
            return
        self.preview_play_token += 1
        if self.playing_mode == "card":
            self.stop_card_preview(reset_image=True)
        if self.player_process and self.player_process.poll() is None:
            if self.playing_clip_index == index and self.playing_mode == "high":
                self.stop_preview()
                return
            self.stop_preview()
        clip = self.current_clip(index)
        if clip is None:
            return
        self.select_clip(index)
        self.start_player(index, Path(clip.path).expanduser().resolve(), "high")

    def start_player(self, index: int, video_path: Path, mode: str) -> None:
        clip = self.current_clip(index)
        if clip is None:
            return
        if not video_path.exists():
            messagebox.showwarning(APP_TITLE, f"视频不存在：{video_path}")
            return
        ffplay = resolve_tool("ffplay")
        if not ffplay:
            messagebox.showerror(APP_TITLE, "没有找到内建播放器 ffplay，请重新打包 App。")
            return
        title = "低清预览" if mode == "preview" else "高清播放"
        command = [
            ffplay,
            "-hide_banner",
            "-loglevel",
            "error",
            "-autoexit",
            "-window_title",
            f"{APP_TITLE} - {title} - Highlight #{index + 1:03d}",
            str(video_path),
        ]
        try:
            self.player_process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                **hidden_subprocess_kwargs(),
            )
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"播放器启动失败: {exc}")
            return
        self.playing_clip_index = index
        self.playing_mode = mode
        if mode == "high":
            self.set_play_button_text(index, "停止播放")
        self.status.set(f"{title}: Highlight #{index + 1:03d}")
        self.root.after(500, self.watch_player)

    def watch_player(self) -> None:
        if self.player_process is None:
            return
        if self.player_process.poll() is None:
            self.root.after(500, self.watch_player)
            return
        self.player_process = None
        if self.playing_clip_index is not None and self.playing_mode == "high":
            self.set_play_button_text(self.playing_clip_index, "高清播放")
        if self.status.get().startswith(("低清预览", "高清播放")):
            self.status.set("完成")
        self.playing_clip_index = None
        self.playing_mode = None

    def stop_preview(self) -> None:
        self.preview_play_token += 1
        self.stop_card_preview(reset_image=True)
        if self.playing_clip_index is not None and self.playing_mode == "high":
            self.set_play_button_text(self.playing_clip_index, "高清播放")
        if self.player_process and self.player_process.poll() is None:
            self.player_process.terminate()
        self.player_process = None
        self.playing_clip_index = None
        self.playing_mode = None

    def set_play_button_text(self, index: int, text: str) -> None:
        button = self.play_buttons.get(index)
        if button is not None:
            button.configure(text=text)

    def delete_selected_clip(self, index: int | None = None) -> None:
        clip = self.current_clip(index)
        if clip is None:
            return
        clip_path = Path(clip.path)
        clip_summary = f"约 {clip.kills} 杀 · {clip.start:.2f}s-{clip.end:.2f}s · {clip.duration:.2f}s"
        if not messagebox.askyesno(APP_TITLE, f"确定删除这个片段吗？\n\n{clip_summary}"):
            return
        self.stop_preview()
        try:
            if clip_path.exists():
                clip_path.unlink()
        except Exception as exc:
            messagebox.showerror(APP_TITLE, f"删除失败: {exc}")
            return
        self.append_log(f"已删除片段: {clip_path.name}\n")
        self.clips = [
            item for item in self.clips if Path(item.path).expanduser().resolve() != clip_path
        ]
        self.refresh_clip_cards()
        if self.clips:
            self.select_clip(0)
        else:
            self.selected_clip = None
            self.selected_clip_index = None

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
            f"fps={CARD_PREVIEW_FPS},scale={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT}:force_original_aspect_ratio=decrease:flags=lanczos,"
            f"pad={THUMBNAIL_WIDTH}:{THUMBNAIL_HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black",
            "-q:v",
            "3",
            str(temporary_dir / "frame_%05d.jpg"),
        ]
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

    def card_preview_cache_key(self, clip: ClipSegment) -> str:
        clip_path = Path(clip.path).expanduser().resolve()
        stat = clip_path.stat()
        source = (
            f"{clip_path}:{stat.st_size}:{stat.st_mtime_ns}:"
            f"card_preview={THUMBNAIL_WIDTH}x{THUMBNAIL_HEIGHT}:fps={CARD_PREVIEW_FPS}:q=3"
        )
        return hashlib.sha1(source.encode("utf-8")).hexdigest()

    def load_card_preview_images(self, frames: list[Path]) -> list[ImageTk.PhotoImage]:
        images: list[ImageTk.PhotoImage] = []
        for frame in frames:
            with Image.open(frame) as image:
                images.append(ImageTk.PhotoImage(image.copy()))
        return images

    def advance_card_preview(self) -> None:
        index = self.playing_clip_index
        if index is None or self.playing_mode != "card" or not self.card_preview_images:
            return
        label = self.thumbnail_labels.get(index)
        if label is None:
            self.stop_card_preview(reset_image=False)
            return
        if self.card_preview_frame_index >= len(self.card_preview_images):
            self.stop_card_preview()
            if self.status.get().startswith("卡片内预览"):
                self.status.set("完成")
            return
        label.configure(image=self.card_preview_images[self.card_preview_frame_index], text="")
        self.card_preview_frame_index += 1
        self.card_preview_after_id = self.root.after(int(1000 / CARD_PREVIEW_FPS), self.advance_card_preview)

    def stop_card_preview(self, reset_image: bool = True) -> None:
        if self.card_preview_after_id:
            self.root.after_cancel(self.card_preview_after_id)
            self.card_preview_after_id = None
        if reset_image and self.playing_clip_index is not None and self.playing_mode == "card":
            label = self.thumbnail_labels.get(self.playing_clip_index)
            photo = self.thumbnail_photos.get(self.playing_clip_index)
            if label is not None:
                if photo is not None:
                    label.configure(image=photo, text="")
                else:
                    label.configure(image="", text="生成低清预览中")
        self.card_preview_images = []
        self.card_preview_frame_index = 0
        if self.playing_mode == "card":
            self.playing_clip_index = None
            self.playing_mode = None

    def _thumbnail_worker(self, generation: int, index: int, clip: ClipSegment, seek_seconds: float) -> None:
        try:
            thumbnail_path = self.thumbnail_for(clip, seek_seconds)
            self.events.put(("thumbnail_ready", (generation, index, thumbnail_path)))
        except Exception:
            self.events.put(("thumbnail_error", (generation, index)))

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
            str(thumbnail_path),
        ]
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **hidden_subprocess_kwargs(),
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "生成低清预览失败")
        return thumbnail_path

    def thumbnail_seek_seconds(self, clip: ClipSegment) -> float:
        if clip.duration <= 0.3:
            return 0.0
        preferred = max(0.1, float(self.seconds_before.get()))
        return min(preferred, max(0.0, clip.duration - 0.2))

    def thumbnail_cache_key(self, clip: ClipSegment, seek_seconds: float) -> str:
        clip_path = Path(clip.path).expanduser().resolve()
        stat = clip_path.stat()
        source = (
            f"{clip_path}:{stat.st_size}:{stat.st_mtime_ns}:"
            f"{THUMBNAIL_WIDTH}x{THUMBNAIL_HEIGHT}:{seek_seconds:.3f}"
        )
        return hashlib.sha1(source.encode("utf-8")).hexdigest()

    def _handle_thumbnail_ready(self, generation: int, index: int, image_path: Path) -> None:
        if generation != self.thumbnail_generation or index not in self.thumbnail_labels:
            return
        with Image.open(image_path) as image:
            photo = ImageTk.PhotoImage(self.fit_thumbnail(image))
        self.thumbnail_photos[index] = photo
        if self.playing_mode == "card" and self.playing_clip_index == index:
            return
        self.thumbnail_labels[index].configure(image=photo, text="")

    def _handle_thumbnail_error(self, generation: int, index: int) -> None:
        if generation != self.thumbnail_generation or index not in self.thumbnail_labels:
            return
        self.thumbnail_labels[index].configure(text="低清预览生成失败")

    @staticmethod
    def fit_thumbnail(image: Image.Image) -> Image.Image:
        image = image.convert("RGB")
        image.thumbnail((THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), Image.Resampling.BICUBIC)
        fitted = Image.new("RGB", (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), (20, 20, 20))
        left = (THUMBNAIL_WIDTH - image.width) // 2
        top = (THUMBNAIL_HEIGHT - image.height) // 2
        fitted.paste(image, (left, top))
        overlay = Image.new("RGBA", fitted.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        center_x = THUMBNAIL_WIDTH // 2
        center_y = THUMBNAIL_HEIGHT // 2
        draw.ellipse(
            (center_x - 22, center_y - 22, center_x + 22, center_y + 22),
            fill=(0, 0, 0, 110),
        )
        draw.polygon(
            [
                (center_x - 7, center_y - 13),
                (center_x - 7, center_y + 13),
                (center_x + 15, center_y),
            ],
            fill=(255, 255, 255, 220),
        )
        fitted = Image.alpha_composite(fitted.convert("RGBA"), overlay).convert("RGB")
        return fitted

    @staticmethod
    def _format_seconds(value: float) -> str:
        minutes = int(value // 60)
        seconds = int(round(value % 60))
        return f"{minutes}:{seconds:02d}"

    @staticmethod
    def _format_size(value: int) -> str:
        gb = value / 1024 / 1024 / 1024
        if gb >= 1:
            return f"{gb:.2f} GB"
        return f"{value / 1024 / 1024:.1f} MB"

    def run(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        self.stop_preview()
        self.root.destroy()


def main() -> None:
    DesktopApp().run()


if __name__ == "__main__":
    main()
