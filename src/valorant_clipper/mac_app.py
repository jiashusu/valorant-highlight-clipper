from __future__ import annotations

import queue
import subprocess
import threading
import webbrowser
from pathlib import Path
from typing import Any

import objc
from AppKit import (
    NSAlert,
    NSAlertFirstButtonReturn,
    NSApp,
    NSApplication,
    NSApplicationActivationPolicyRegular,
    NSBackingStoreBuffered,
    NSBezelStyleRounded,
    NSButton,
    NSButtonTypeMomentaryPushIn,
    NSButtonTypeSwitch,
    NSColor,
    NSFocusRingTypeNone,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
    NSGradient,
    NSImage,
    NSImageScaleProportionallyUpOrDown,
    NSImageView,
    NSLineBreakByTruncatingMiddle,
    NSMakeRect,
    NSMakeSize,
    NSModalResponseOK,
    NSOpenPanel,
    NSProgressIndicator,
    NSProgressIndicatorStyleBar,
    NSScrollView,
    NSSelectorFromString,
    NSTableColumn,
    NSTableView,
    NSTableViewSelectionHighlightStyleRegular,
    NSTextField,
    NSTextFieldCell,
    NSTextView,
    NSTimer,
    NSView,
    NSVisualEffectBlendingModeWithinWindow,
    NSVisualEffectMaterialHUDWindow,
    NSVisualEffectStateActive,
    NSVisualEffectView,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSAttributedString, NSMakeRange, NSObject
from PyObjCTools import AppHelper

from .build_info import BUILD_SHA
from .core import (
    ClipSegment,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SOURCE_DIR,
    VideoInfo,
    discover_videos,
    hidden_subprocess_kwargs,
    process_video,
    resolve_tool,
)
from .preview_cache import CARD_PREVIEW_FPS, PreviewCache
from .update_checker import UpdateResult, check_for_update


APP_TITLE = "Valorant 高光剪辑"
APP_VERSION = "macOS v1.3.2"
AUTHOR_URL = "https://github.com/jiashusu/valorant-highlight-clipper"
UPDATE_CHECK_INTERVAL_SECONDS = 30 * 60
VIDEO_EXTENSIONS = ["mp4", "mov", "mkv", "avi", "m4v", "flv"]

WINDOW_WIDTH = 1720
WINDOW_HEIGHT = 980
CLIP_COLUMNS = 3


def short_build() -> str:
    value = (BUILD_SHA or "").strip()
    if not value or value == "unknown":
        return "local"
    return value[:7]


def ns_color(hex_value: str, alpha: float = 1.0) -> NSColor:
    value = hex_value.strip().lstrip("#")
    red = int(value[0:2], 16) / 255
    green = int(value[2:4], 16) / 255
    blue = int(value[4:6], 16) / 255
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(red, green, blue, alpha)


COLORS = {
    "bg_top": ns_color("#050506"),
    "bg_bottom": ns_color("#0B0B0D"),
    "panel": ns_color("#18181B", 0.62),
    "panel_border": ns_color("#FFFFFF", 0.075),
    "field": ns_color("#0D0D10", 0.80),
    "field_soft": ns_color("#151519", 0.66),
    "card": ns_color("#1D1D22", 0.76),
    "text": ns_color("#F6F8FC"),
    "muted": ns_color("#A8ABB2"),
    "subtle": ns_color("#737780"),
    "accent": ns_color("#64D2FF"),
    "accent_hover": ns_color("#87DEFF"),
    "accent_text": ns_color("#071018"),
    "danger": ns_color("#FF6B7A", 0.22),
    "danger_text": ns_color("#FFD8DD"),
    "warning_bg": ns_color("#241F10", 0.58),
    "warning_text": ns_color("#FFD84D"),
    "link": ns_color("#7DDCFF"),
}


TEXTS = {
    "zh": {
        "app_title": APP_TITLE,
        "author": "原作者: shu",
        "language_toggle": "EN",
        "check_update": "检查更新",
        "paths": "路径",
        "source": "素材文件夹或视频文件",
        "choose_folder": "选择文件夹",
        "choose_video": "选择视频",
        "recursive": "递归扫描",
        "output_dir": "输出目录",
        "choose_output": "选择输出目录",
        "open_output": "打开输出目录",
        "settings": "参数",
        "confidence": "置信度",
        "framerate": "识别帧率",
        "seconds_before": "提前秒数",
        "seconds_after": "延后秒数",
        "merge_gap": "合并间隔",
        "min_event": "最短事件秒",
        "max_seconds": "最多分析秒数",
        "strict": "严格过滤队友击杀（推荐）",
        "copy_streams": "快速无损截取",
        "scan_videos": "扫描视频",
        "clear_log": "清空日志",
        "video": "视频",
        "duration": "时长",
        "size": "大小",
        "path": "路径",
        "process_log": "处理日志",
        "highlights": "Highlights",
        "preview_mode": "低清预览 / 高清播放",
        "warning": "提示：当前版本仍可能输出队友击杀片段，可先手动删除；后续会继续更新识别逻辑。",
        "empty_title": "还没有高光片段",
        "empty_detail": "扫描并开始剪辑后，这里会显示低清预览、约几杀、高清播放、定位视频和删除按钮。",
        "preparing_title": "正在准备新的剪辑",
        "preparing_detail": "高光片段导出后会自动出现在这里。",
        "no_clips_title": "没有导出片段",
        "no_clips_detail": "这次没有识别到满足条件的高光。可以降低置信度、缩短最短事件秒数，或关闭严格过滤后再试。",
        "play": "播放",
        "play_high": "高清播放",
        "stop_play": "停止播放",
        "reveal": "定位",
        "delete": "删除",
        "confirm": "确定",
        "cancel": "取消",
        "start": "开始剪辑",
        "ready": "准备就绪",
        "scanning": "扫描中",
        "checking_update": "检查更新中",
        "trimming": "剪辑中",
        "error": "出错",
        "done": "完成",
        "up_to_date": "已是最新版本",
        "update_failed": "检查更新失败",
        "new_version": "有新版本: {version}",
        "scan_done": "扫描完成: {count} 个视频",
        "select_video_first": "请先扫描并选择一个视频。",
        "busy": "当前任务还在运行，请等它完成。",
        "cut_failed": "剪辑失败: {error}",
        "scan_failed": "扫描失败: {error}",
        "preview_generating": "生成预览中",
        "low_preview": "低清预览",
        "preview_failed": "预览失败",
        "preview_no_frames": "预览失败: 没有可播放帧",
        "thumbnail_failed": "低清预览生成失败",
        "missing_ffplay": "ffplay 不可用，无法高清播放。",
        "high_playing": "高清播放",
        "delete_confirm": "确定删除这个片段吗？\n\n约 {kills} 杀 · {start:.2f}s - {end:.2f}s",
        "delete_failed": "删除失败: {error}",
        "deleted_log": "已删除片段: {name}\n",
        "finished_log": "完成，导出 {count} 个片段\n",
        "clip_info": "约 {kills} 杀 · {duration:.2f}s\n{start:.2f}s - {end:.2f}s",
        "update_open": "{message}\n\n是否打开 GitHub Actions 下载新版 macOS App？",
    },
    "en": {
        "app_title": "Valorant Highlight Clipper",
        "author": "Author: shu",
        "language_toggle": "中文",
        "check_update": "Check Updates",
        "paths": "Paths",
        "source": "Source folder or video file",
        "choose_folder": "Folder",
        "choose_video": "Video",
        "recursive": "Recursive",
        "output_dir": "Output folder",
        "choose_output": "Choose output",
        "open_output": "Open output",
        "settings": "Settings",
        "confidence": "Confidence",
        "framerate": "Scan FPS",
        "seconds_before": "Before seconds",
        "seconds_after": "After seconds",
        "merge_gap": "Merge gap",
        "min_event": "Min event sec",
        "max_seconds": "Max scan sec",
        "strict": "Strict own-kill filter",
        "copy_streams": "Fast stream copy",
        "scan_videos": "Scan Videos",
        "clear_log": "Clear Log",
        "video": "Videos",
        "duration": "Duration",
        "size": "Size",
        "path": "Path",
        "process_log": "Process Log",
        "highlights": "Highlights",
        "preview_mode": "Low preview / HD playback",
        "warning": "Note: this version may still export teammate kills. Delete them manually for now; detection will keep improving.",
        "empty_title": "No highlights yet",
        "empty_detail": "After clipping, low previews, kill count, HD playback, reveal and delete actions will appear here.",
        "preparing_title": "Preparing new clips",
        "preparing_detail": "Exported highlights will appear here automatically.",
        "no_clips_title": "No exported clips",
        "no_clips_detail": "No matching highlights were detected. Try lowering confidence, shortening min event seconds, or disabling strict filtering.",
        "play": "Play",
        "play_high": "HD Play",
        "stop_play": "Stop",
        "reveal": "Reveal",
        "delete": "Delete",
        "confirm": "OK",
        "cancel": "Cancel",
        "start": "Start Clipping",
        "ready": "Ready",
        "scanning": "Scanning",
        "checking_update": "Checking updates",
        "trimming": "Clipping",
        "error": "Error",
        "done": "Done",
        "up_to_date": "Up to date",
        "update_failed": "Update failed",
        "new_version": "New version: {version}",
        "scan_done": "Scan complete: {count} videos",
        "select_video_first": "Scan and select a video first.",
        "busy": "Another task is still running.",
        "cut_failed": "Clipping failed: {error}",
        "scan_failed": "Scan failed: {error}",
        "preview_generating": "Generating preview",
        "low_preview": "Low preview",
        "preview_failed": "Preview failed",
        "preview_no_frames": "Preview failed: no playable frames",
        "thumbnail_failed": "Preview generation failed",
        "missing_ffplay": "ffplay is unavailable, so HD playback cannot start.",
        "high_playing": "HD playback",
        "delete_confirm": "Delete this clip?\n\n~{kills} kills · {start:.2f}s - {end:.2f}s",
        "delete_failed": "Delete failed: {error}",
        "deleted_log": "Deleted clip: {name}\n",
        "finished_log": "Done, exported {count} clips\n",
        "clip_info": "~{kills} kills · {duration:.2f}s\n{start:.2f}s - {end:.2f}s",
        "update_open": "{message}\n\nOpen GitHub Actions to download the new macOS App?",
    },
}


class FlippedView(NSView):
    def isFlipped(self) -> bool:
        return True


class GlassEffectView(NSVisualEffectView):
    def isFlipped(self) -> bool:
        return True


class GradientView(FlippedView):
    def drawRect_(self, rect) -> None:
        gradient = NSGradient.alloc().initWithStartingColor_endingColor_(
            COLORS["bg_top"],
            COLORS["bg_bottom"],
        )
        gradient.drawInRect_angle_(self.bounds(), 90)


class CenteredTextFieldCell(NSTextFieldCell):
    def drawingRectForBounds_(self, rect):
        drawing = objc.super(CenteredTextFieldCell, self).drawingRectForBounds_(rect)
        cell_size = self.cellSizeForBounds_(rect)
        drawing.origin.y = rect.origin.y + max(0, (rect.size.height - cell_size.height) / 2) - 1
        return drawing


def set_layer(view, radius: float, background: NSColor | None = None, border: NSColor | None = None) -> None:
    view.setWantsLayer_(True)
    layer = view.layer()
    layer.setCornerRadius_(radius)
    layer.setMasksToBounds_(True)
    if background is not None:
        layer.setBackgroundColor_(background.CGColor())
    if border is not None:
        layer.setBorderWidth_(1)
        layer.setBorderColor_(border.CGColor())


def glass_view(frame, radius: float = 22, background: NSColor | None = None):
    view = FlippedView.alloc().initWithFrame_(frame)
    set_layer(view, radius, background or COLORS["panel"], COLORS["panel_border"])
    return view


def visual_glass_view(frame, radius: float = 22):
    view = GlassEffectView.alloc().initWithFrame_(frame)
    view.setMaterial_(NSVisualEffectMaterialHUDWindow)
    view.setBlendingMode_(NSVisualEffectBlendingModeWithinWindow)
    view.setState_(NSVisualEffectStateActive)
    set_layer(view, radius, border=COLORS["panel_border"])
    return view


def label(text: str, frame, size: float = 13, weight: float = 0.0, color: NSColor | None = None):
    item = NSTextField.labelWithString_(text)
    item.setFrame_(frame)
    item.setTextColor_(color or COLORS["text"])
    item.setFont_(NSFont.systemFontOfSize_weight_(size, weight))
    item.setLineBreakMode_(NSLineBreakByTruncatingMiddle)
    return item


def text_field(value: str, frame):
    field = NSTextField.alloc().initWithFrame_(frame)
    cell = CenteredTextFieldCell.alloc().initTextCell_(value)
    field.setCell_(cell)
    field.setStringValue_(value)
    field.setBezeled_(False)
    field.setDrawsBackground_(True)
    field.setBackgroundColor_(COLORS["field"])
    field.setTextColor_(COLORS["text"])
    field.setFont_(NSFont.systemFontOfSize_(13))
    field.setFocusRingType_(NSFocusRingTypeNone)
    set_layer(field, 12, COLORS["field"], COLORS["panel_border"])
    return field


def attributed_title(text: str, color: NSColor, size: float = 13, weight: float = 0.0):
    attrs = {
        NSForegroundColorAttributeName: color,
        NSFontAttributeName: NSFont.systemFontOfSize_weight_(size, weight),
    }
    return NSAttributedString.alloc().initWithString_attributes_(text, attrs)


def button(title: str, frame, target, action: str, kind: str = "secondary"):
    item = NSButton.alloc().initWithFrame_(frame)
    item.setTitle_(title)
    item.setTarget_(target)
    item.setAction_(NSSelectorFromString(action))
    item.setButtonType_(NSButtonTypeMomentaryPushIn)
    item.setBezelStyle_(NSBezelStyleRounded)
    item.setBordered_(False)
    item.setFocusRingType_(NSFocusRingTypeNone)
    item.setRefusesFirstResponder_(True)
    if kind == "primary":
        bg, fg = COLORS["accent"], COLORS["accent_text"]
    elif kind == "danger":
        bg, fg = COLORS["danger"], COLORS["danger_text"]
    elif kind == "link":
        bg, fg = ns_color("#FFFFFF", 0.0), COLORS["link"]
    else:
        bg, fg = ns_color("#FFFFFF", 0.08), COLORS["text"]
    item.setAttributedTitle_(attributed_title(title, fg, 13, 0.28))
    border = ns_color("#FFFFFF", 0.0) if kind == "link" else ns_color("#FFFFFF", 0.10)
    set_layer(item, 17, bg, border)
    return item


def checkbox(title: str, frame, state: bool = False):
    item = NSButton.alloc().initWithFrame_(frame)
    item.setButtonType_(NSButtonTypeSwitch)
    item.setFocusRingType_(NSFocusRingTypeNone)
    item.setAttributedTitle_(attributed_title(title, COLORS["text"], 13, 0.12))
    item.setState_(1 if state else 0)
    return item


def format_seconds(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{sec:02d}"
    return f"{minutes}:{sec:02d}"


def format_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


class MacClipperController(NSObject):
    def init(self):
        self = objc.super(MacClipperController, self).init()
        if self is None:
            return None
        self.videos: list[VideoInfo] = []
        self.clips: list[ClipSegment] = []
        self.selected_video: Path | None = None
        self.selected_clip_index: int | None = None
        self.worker_thread: threading.Thread | None = None
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.preview_cache = PreviewCache("valorant_clipper_appkit")
        self.thumbnail_generation = 0
        self.thumbnail_views: dict[int, NSImageView] = {}
        self.thumbnail_paths: dict[int, Path] = {}
        self.play_buttons: dict[int, NSButton] = {}
        self.preview_timer = None
        self.preview_frames: list[NSImage] = []
        self.preview_frame_index = 0
        self.preview_play_token = 0
        self.playing_clip_index: int | None = None
        self.playing_mode: str | None = None
        self.player_process: subprocess.Popen[str] | None = None
        self.last_update_prompt_sha: str | None = None
        self.language = "zh"
        self.localized_labels: list[tuple[Any, str]] = []
        self.localized_buttons: list[tuple[Any, str, str]] = []
        self.status_key = "ready"
        self.status_kwargs: dict[str, Any] = {}
        self.empty_state_key: tuple[str, str] | None = None
        return self

    def show(self) -> None:
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable
        )
        rect = NSMakeRect(80, 80, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            style,
            NSBackingStoreBuffered,
            False,
        )
        self.window.setTitle_(APP_TITLE)
        self.window.setMinSize_(NSMakeSize(1360, 840))
        self.window.setReleasedWhenClosed_(False)
        self.root = GradientView.alloc().initWithFrame_(NSMakeRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT))
        self.root.setAutoresizingMask_(18)
        self.window.setContentView_(self.root)
        self.build_ui()
        self.apply_language()
        self.window.makeKeyAndOrderFront_(None)
        self.window.makeFirstResponder_(None)
        NSApp.activateIgnoringOtherApps_(True)
        self.drain_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.1,
            self,
            NSSelectorFromString("drainEvents:"),
            None,
            True,
        )
        self.update_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.5,
            self,
            NSSelectorFromString("initialUpdateCheck:"),
            None,
            False,
        )

    @objc.python_method
    def text(self, key: str, **kwargs) -> str:
        template = TEXTS.get(self.language, TEXTS["zh"]).get(key, TEXTS["zh"].get(key, key))
        return template.format(**kwargs) if kwargs else template

    @objc.python_method
    def localized_label(self, key: str, frame, size: float = 13, weight: float = 0.0, color: NSColor | None = None):
        item = label(self.text(key), frame, size, weight, color)
        self.localized_labels.append((item, key))
        return item

    @objc.python_method
    def localized_button(self, key: str, frame, action: str, kind: str = "secondary"):
        item = button(self.text(key), frame, self, action, kind)
        self.localized_buttons.append((item, key, kind))
        return item

    @objc.python_method
    def set_button_text(self, item, text: str, kind: str = "secondary") -> None:
        if kind == "primary":
            color = COLORS["accent_text"]
        elif kind == "danger":
            color = COLORS["danger_text"]
        elif kind == "link":
            color = COLORS["link"]
        else:
            color = COLORS["text"]
        item.setAttributedTitle_(attributed_title(text, color, 13, 0.28))

    @objc.python_method
    def set_status(self, key: str, **kwargs) -> None:
        self.status_key = key
        self.status_kwargs = kwargs
        self.status_label.setStringValue_(self.text(key, **kwargs))

    @objc.python_method
    def apply_language(self) -> None:
        self.window.setTitle_(self.text("app_title"))
        for item, key in self.localized_labels:
            item.setStringValue_(self.text(key))
        for item, key, kind in self.localized_buttons:
            self.set_button_text(item, self.text(key), kind)
        if hasattr(self, "status_label"):
            self.status_label.setStringValue_(self.text(self.status_key, **self.status_kwargs))
        if hasattr(self, "warning_label"):
            self.warning_label.setStringValue_(self.text("warning"))
        if hasattr(self, "table_columns"):
            for key, column in self.table_columns.items():
                column.setTitle_(self.text(key))
        if self.empty_state_key is not None and not self.clips:
            self.show_empty_clips(*self.empty_state_key)
        if self.clips:
            self.refresh_clip_cards()

    def toggleLanguage_(self, _sender) -> None:
        self.language = "en" if self.language == "zh" else "zh"
        self.apply_language()

    def openAuthor_(self, _sender) -> None:
        webbrowser.open(AUTHOR_URL)

    @objc.python_method
    def build_ui(self) -> None:
        self.build_header()
        self.left_panel = visual_glass_view(NSMakeRect(18, 76, 680, 790), 22)
        self.right_panel = visual_glass_view(NSMakeRect(716, 76, 986, 790), 22)
        self.root.addSubview_(self.left_panel)
        self.root.addSubview_(self.right_panel)
        self.build_left_panel()
        self.build_right_panel()
        self.progress = NSProgressIndicator.alloc().initWithFrame_(NSMakeRect(18, 886, 1540, 16))
        self.progress.setIndeterminate_(False)
        self.progress.setMinValue_(0)
        self.progress.setMaxValue_(100)
        self.progress.setDoubleValue_(0)
        self.progress.setStyle_(NSProgressIndicatorStyleBar)
        self.root.addSubview_(self.progress)
        self.start_button = self.localized_button("start", NSMakeRect(1575, 874, 126, 42), "startJob:", "primary")
        self.root.addSubview_(self.start_button)

    @objc.python_method
    def build_header(self) -> None:
        self.root.addSubview_(self.localized_label("app_title", NSMakeRect(22, 22, 180, 28), 14, 0.22))
        self.root.addSubview_(
            label(f"{APP_VERSION} · {short_build()}", NSMakeRect(200, 22, 190, 28), 13, 0.20, COLORS["accent"])
        )
        self.root.addSubview_(self.localized_button("author", NSMakeRect(1268, 16, 112, 38), "openAuthor:", "link"))
        self.root.addSubview_(self.localized_button("language_toggle", NSMakeRect(1388, 16, 58, 38), "toggleLanguage:", "secondary"))
        self.status_label = label(self.text("ready"), NSMakeRect(1452, 22, 120, 28), 13, 0.12, COLORS["muted"])
        self.status_label.setAlignment_(2)
        self.root.addSubview_(self.status_label)
        self.root.addSubview_(self.localized_button("check_update", NSMakeRect(1580, 16, 120, 38), "checkUpdates:", "secondary"))

    @objc.python_method
    def build_left_panel(self) -> None:
        x, y, w = 24, 18, 632
        self.left_panel.addSubview_(self.localized_label("paths", NSMakeRect(x, y, 100, 28), 18, 0.28))
        self.left_panel.addSubview_(self.localized_label("source", NSMakeRect(x, y + 45, 240, 22), 13, 0.22))
        self.source_field = text_field(str(DEFAULT_SOURCE_DIR), NSMakeRect(x, y + 70, w, 30))
        self.left_panel.addSubview_(self.source_field)
        self.left_panel.addSubview_(self.localized_button("choose_folder", NSMakeRect(x, y + 112, 128, 36), "chooseSourceFolder:", "secondary"))
        self.left_panel.addSubview_(self.localized_button("choose_video", NSMakeRect(x + 140, y + 112, 118, 36), "chooseSourceFile:", "secondary"))
        self.recursive_check = checkbox(self.text("recursive"), NSMakeRect(x + 274, y + 116, 120, 28), False)
        self.localized_buttons.append((self.recursive_check, "recursive", "secondary"))
        self.left_panel.addSubview_(self.recursive_check)

        self.left_panel.addSubview_(self.localized_label("output_dir", NSMakeRect(x, y + 165, 120, 22), 13, 0.22))
        self.output_field = text_field(str(DEFAULT_OUTPUT_DIR), NSMakeRect(x, y + 190, w, 30))
        self.left_panel.addSubview_(self.output_field)
        self.left_panel.addSubview_(self.localized_button("choose_output", NSMakeRect(x, y + 232, 140, 36), "chooseOutputDir:", "secondary"))
        self.left_panel.addSubview_(self.localized_button("open_output", NSMakeRect(x + 152, y + 232, 140, 36), "openOutputDir:", "secondary"))

        self.left_panel.addSubview_(self.localized_label("settings", NSMakeRect(x, y + 305, 100, 28), 18, 0.28))
        self.confidence_field = self.add_number_row("confidence", "0.93", x, y + 350)
        self.framerate_field = self.add_number_row("framerate", "8", x + 330, y + 350)
        self.before_field = self.add_number_row("seconds_before", "4.0", x, y + 395)
        self.after_field = self.add_number_row("seconds_after", "0.5", x + 330, y + 395)
        self.merge_field = self.add_number_row("merge_gap", "3.0", x, y + 440)
        self.min_event_field = self.add_number_row("min_event", "0.75", x + 330, y + 440)
        self.max_seconds_field = self.add_number_row("max_seconds", "", x, y + 485)
        self.strict_check = checkbox(self.text("strict"), NSMakeRect(x, y + 535, 230, 28), True)
        self.copy_check = checkbox(self.text("copy_streams"), NSMakeRect(x + 330, y + 535, 150, 28), False)
        self.localized_buttons.append((self.strict_check, "strict", "secondary"))
        self.localized_buttons.append((self.copy_check, "copy_streams", "secondary"))
        self.left_panel.addSubview_(self.strict_check)
        self.left_panel.addSubview_(self.copy_check)
        self.left_panel.addSubview_(self.localized_button("scan_videos", NSMakeRect(x, y + 592, 120, 38), "scanVideos:", "secondary"))
        self.left_panel.addSubview_(self.localized_button("clear_log", NSMakeRect(x + 132, y + 592, 120, 38), "clearLog:", "secondary"))

        self.left_panel.addSubview_(self.localized_label("video", NSMakeRect(x, y + 650, 100, 24), 16, 0.24))
        self.video_table = self.make_video_table(NSMakeRect(x, y + 680, w, 94))
        self.left_panel.addSubview_(self.video_table["scroll"])

    @objc.python_method
    def add_number_row(self, key: str, value: str, x: float, y: float):
        self.left_panel.addSubview_(self.localized_label(key, NSMakeRect(x, y, 110, 26), 13, 0.18))
        field = text_field(value, NSMakeRect(x + 112, y - 2, 170, 30))
        self.left_panel.addSubview_(field)
        return field

    @objc.python_method
    def make_video_table(self, frame):
        scroll = NSScrollView.alloc().initWithFrame_(frame)
        table = NSTableView.alloc().initWithFrame_(NSMakeRect(0, 0, frame.size.width, frame.size.height))
        table.setSelectionHighlightStyle_(NSTableViewSelectionHighlightStyleRegular)
        table.setUsesAlternatingRowBackgroundColors_(False)
        table.setGridStyleMask_(0)
        table.setRowHeight_(26)
        self.table_columns = {}
        columns = [("duration", "duration", 72), ("size", "size", 88), ("path", "path", 448)]
        for ident, key, width in columns:
            column = NSTableColumn.alloc().initWithIdentifier_(ident)
            column.setTitle_(self.text(key))
            column.setWidth_(width)
            table.addTableColumn_(column)
            self.table_columns[key] = column
        table.setDataSource_(self)
        table.setDelegate_(self)
        scroll.setDocumentView_(table)
        scroll.setHasVerticalScroller_(True)
        scroll.setDrawsBackground_(False)
        set_layer(scroll, 14, COLORS["field"], COLORS["panel_border"])
        self._video_table_view = table
        return {"scroll": scroll, "table": table}

    @objc.python_method
    def build_right_panel(self) -> None:
        self.right_panel.addSubview_(self.localized_label("process_log", NSMakeRect(24, 18, 100, 28), 18, 0.28))
        self.log_view = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, 930, 206))
        self.log_view.setEditable_(False)
        self.log_view.setTextColor_(COLORS["text"])
        self.log_view.setFont_(NSFont.monospacedSystemFontOfSize_weight_(12, 0))
        self.log_view.setBackgroundColor_(COLORS["field"])
        log_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(24, 50, 938, 216))
        log_scroll.setDocumentView_(self.log_view)
        log_scroll.setHasVerticalScroller_(True)
        log_scroll.setDrawsBackground_(False)
        set_layer(log_scroll, 16, COLORS["field"], COLORS["panel_border"])
        self.right_panel.addSubview_(log_scroll)

        self.right_panel.addSubview_(self.localized_label("highlights", NSMakeRect(24, 292, 180, 26), 18, 0.28))
        self.right_panel.addSubview_(
            self.localized_label("preview_mode", NSMakeRect(760, 292, 200, 26), 13, 0.14, COLORS["muted"])
        )
        warning = glass_view(NSMakeRect(24, 326, 938, 42), 14, COLORS["warning_bg"])
        self.warning_label = self.localized_label("warning", NSMakeRect(14, 10, 900, 22), 13, 0.18, COLORS["warning_text"])
        warning.addSubview_(self.warning_label)
        self.right_panel.addSubview_(warning)
        self.clips_scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(24, 386, 938, 378))
        self.clips_content = FlippedView.alloc().initWithFrame_(NSMakeRect(0, 0, 938, 378))
        self.clips_scroll.setDocumentView_(self.clips_content)
        self.clips_scroll.setHasVerticalScroller_(True)
        self.clips_scroll.setDrawsBackground_(False)
        set_layer(self.clips_scroll, 18, ns_color("#080809", 0.24), None)
        self.right_panel.addSubview_(self.clips_scroll)
        self.show_empty_clips("empty_title", "empty_detail")

    @objc.python_method
    def show_empty_clips(self, title_key: str, detail_key: str) -> None:
        self.empty_state_key = (title_key, detail_key)
        for subview in list(self.clips_content.subviews()):
            subview.removeFromSuperview()
        card = glass_view(NSMakeRect(22, 28, 560, 108), 22, ns_color("#202025", 0.62))
        card.addSubview_(label(self.text(title_key), NSMakeRect(26, 24, 500, 24), 16, 0.28))
        card.addSubview_(label(self.text(detail_key), NSMakeRect(26, 58, 500, 28), 13, 0.0, COLORS["muted"]))
        self.clips_content.addSubview_(card)

    @objc.python_method
    def append_log(self, message: str) -> None:
        current = str(self.log_view.string() or "")
        text = current + message
        self.log_view.setString_(text)
        self.log_view.scrollRangeToVisible_(NSMakeRange(len(text), 0))

    def clearLog_(self, _sender) -> None:
        self.log_view.setString_("")

    def chooseSourceFolder_(self, _sender) -> None:
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseDirectories_(True)
        panel.setCanChooseFiles_(False)
        panel.setAllowsMultipleSelection_(False)
        if panel.runModal() == NSModalResponseOK:
            self.source_field.setStringValue_(panel.URL().path())
            self.scanVideos_(None)

    def chooseSourceFile_(self, _sender) -> None:
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseDirectories_(False)
        panel.setCanChooseFiles_(True)
        panel.setAllowsMultipleSelection_(False)
        panel.setAllowedFileTypes_(VIDEO_EXTENSIONS)
        if panel.runModal() == NSModalResponseOK:
            self.source_field.setStringValue_(panel.URL().path())
            self.scanVideos_(None)

    def chooseOutputDir_(self, _sender) -> None:
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseDirectories_(True)
        panel.setCanChooseFiles_(False)
        panel.setAllowsMultipleSelection_(False)
        if panel.runModal() == NSModalResponseOK:
            self.output_field.setStringValue_(panel.URL().path())

    def openOutputDir_(self, _sender) -> None:
        path = Path(str(self.output_field.stringValue())).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["open", str(path)])

    def scanVideos_(self, _sender) -> None:
        source = Path(str(self.source_field.stringValue())).expanduser()
        recursive = bool(self.recursive_check.state())
        self.set_status("scanning")
        self.run_worker(lambda: self.scan_worker(source, recursive))

    @objc.python_method
    def scan_worker(self, source: Path, recursive: bool) -> None:
        try:
            videos = discover_videos(source, recursive=recursive)
            self.events.put(("videos", videos))
        except Exception as exc:
            self.events.put(("error", self.text("scan_failed", error=exc)))
        finally:
            self.events.put(("worker_done", None))

    def startJob_(self, _sender) -> None:
        if self.selected_video is None:
            self.select_first_video()
        if self.selected_video is None:
            self.show_alert(self.text("select_video_first"))
            return
        self.stop_preview()
        self.clips = []
        self.selected_clip_index = None
        self.show_empty_clips("preparing_title", "preparing_detail")
        self.start_button.setEnabled_(False)
        self.progress.setDoubleValue_(0)
        self.set_status("trimming")
        config = {
            "video_path": self.selected_video,
            "output_dir": Path(str(self.output_field.stringValue())).expanduser(),
            "confidence": float(str(self.confidence_field.stringValue())),
            "framerate": int(float(str(self.framerate_field.stringValue()))),
            "seconds_before": float(str(self.before_field.stringValue())),
            "seconds_after": float(str(self.after_field.stringValue())),
            "merge_gap_seconds": float(str(self.merge_field.stringValue())),
            "max_seconds": self.parse_optional_float(self.max_seconds_field),
            "strict_own_kills": bool(self.strict_check.state()),
            "min_event_seconds": float(str(self.min_event_field.stringValue())),
            "copy_streams": bool(self.copy_check.state()),
        }
        self.run_worker(lambda: self.job_worker(config))

    @objc.python_method
    def parse_optional_float(self, field) -> float | None:
        text = str(field.stringValue()).strip()
        return float(text) if text else None

    @objc.python_method
    def job_worker(self, config: dict[str, Any]) -> None:
        try:
            def progress(message: str, value: float | None = None) -> None:
                self.events.put(("log", f"{message}\n"))
                if value is not None:
                    self.events.put(("progress", value))

            clips = process_video(progress=progress, **config)
            self.events.put(("clips", clips))
        except Exception as exc:
            self.events.put(("error", self.text("cut_failed", error=exc)))
        finally:
            self.events.put(("worker_done", None))

    @objc.python_method
    def run_worker(self, target) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            self.show_alert(self.text("busy"))
            return
        self.worker_thread = threading.Thread(target=target, daemon=True)
        self.worker_thread.start()

    def drainEvents_(self, _timer) -> None:
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "videos":
                self.render_videos(payload)
            elif kind == "log":
                self.append_log(str(payload))
            elif kind == "progress":
                self.progress.setDoubleValue_(max(0, min(100, float(payload) * 100)))
            elif kind == "clips":
                self.render_clips(payload)
            elif kind == "error":
                self.set_status("error")
                self.append_log(f"{payload}\n")
                self.show_alert(str(payload))
            elif kind == "update":
                manual, result = payload
                self.handle_update_result(bool(manual), result)
            elif kind == "update_error":
                manual, message = payload
                self.handle_update_error(bool(manual), str(message))
            elif kind == "thumbnail_ready":
                generation, index, image_path = payload
                self.handle_thumbnail_ready(int(generation), int(index), Path(str(image_path)))
            elif kind == "thumbnail_error":
                generation, index = payload
                self.handle_thumbnail_error(int(generation), int(index))
            elif kind == "card_preview_ready":
                token, index, frames = payload
                self.handle_card_preview_ready(int(token), int(index), frames)
            elif kind == "card_preview_error":
                token, message = payload
                self.handle_card_preview_error(int(token), str(message))
            elif kind == "player_done":
                self.handle_player_done()
            elif kind == "worker_done":
                self.start_button.setEnabled_(True)
                if self.status_key in {"trimming", "preview_generating", "high_playing"}:
                    self.set_status("done")

    def initialUpdateCheck_(self, _timer) -> None:
        self.check_for_updates(False)

    def checkUpdates_(self, _sender) -> None:
        self.check_for_updates(True)

    @objc.python_method
    def check_for_updates(self, manual: bool) -> None:
        self.set_status("checking_update")
        thread = threading.Thread(target=self.update_worker, args=(manual,), daemon=True)
        thread.start()

    @objc.python_method
    def update_worker(self, manual: bool) -> None:
        try:
            self.events.put(("update", (manual, check_for_update())))
        except Exception as exc:
            self.events.put(("update_error", (manual, self.text("update_failed") + f": {exc}")))

    @objc.python_method
    def schedule_next_update_check(self) -> None:
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            UPDATE_CHECK_INTERVAL_SECONDS,
            self,
            NSSelectorFromString("initialUpdateCheck:"),
            None,
            False,
        )

    @objc.python_method
    def handle_update_result(self, manual: bool, result: UpdateResult) -> None:
        if result.update_available:
            if not manual and result.remote_sha == self.last_update_prompt_sha:
                self.schedule_next_update_check()
                return
            self.last_update_prompt_sha = result.remote_sha
            self.set_status("new_version", version=result.remote_short)
            if self.confirm(self.text("update_open", message=result.message)):
                webbrowser.open(result.download_url)
            if not manual:
                self.schedule_next_update_check()
            return

        if manual:
            self.set_status("up_to_date")
            self.show_alert(result.message)
        elif self.status_key == "checking_update":
            self.set_status("ready")
        if not manual:
            self.schedule_next_update_check()

    @objc.python_method
    def handle_update_error(self, manual: bool, message: str) -> None:
        if manual:
            self.set_status("update_failed")
            self.show_alert(message)
        elif self.status_key == "checking_update":
            self.set_status("ready")
        if not manual:
            self.schedule_next_update_check()

    @objc.python_method
    def render_videos(self, videos: list[VideoInfo]) -> None:
        self.videos = list(videos)
        self.selected_video = None
        self._video_table_view.reloadData()
        self.select_first_video()
        self.set_status("scan_done", count=len(self.videos))

    def numberOfRowsInTableView_(self, _tableView) -> int:
        return len(self.videos)

    def tableView_objectValueForTableColumn_row_(self, _tableView, tableColumn, row: int):
        if row < 0 or row >= len(self.videos):
            return ""
        video = self.videos[row]
        ident = str(tableColumn.identifier())
        if ident == "duration":
            return format_seconds(video.duration)
        if ident == "size":
            return format_size(video.size_bytes)
        return video.path

    def tableViewSelectionDidChange_(self, notification) -> None:
        row = notification.object().selectedRow()
        if row >= 0 and row < len(self.videos):
            self.selected_video = Path(self.videos[row].path)

    @objc.python_method
    def select_first_video(self) -> None:
        if not self.videos:
            self.selected_video = None
            return
        self._video_table_view.selectRowIndexes_byExtendingSelection_(objc.lookUpClass("NSIndexSet").indexSetWithIndex_(0), False)
        self.selected_video = Path(self.videos[0].path)

    @objc.python_method
    def render_clips(self, clips: list[ClipSegment]) -> None:
        self.clips = list(clips)
        self.refresh_clip_cards()
        self.append_log(self.text("finished_log", count=len(clips)))
        if self.clips:
            self.select_clip(0)

    @objc.python_method
    def refresh_clip_cards(self) -> None:
        self.stop_preview()
        self.thumbnail_generation += 1
        generation = self.thumbnail_generation
        self.thumbnail_views = {}
        self.thumbnail_paths = {}
        self.play_buttons = {}
        for subview in list(self.clips_content.subviews()):
            subview.removeFromSuperview()
        self.selected_clip_index = None
        if not self.clips:
            self.show_empty_clips("no_clips_title", "no_clips_detail")
            return

        card_w, card_h = 294, 284
        gap_x, gap_y = 16, 16
        rows = (len(self.clips) + CLIP_COLUMNS - 1) // CLIP_COLUMNS
        content_h = max(378, rows * (card_h + gap_y) + 16)
        self.clips_content.setFrame_(NSMakeRect(0, 0, 938, content_h))
        for index, clip in enumerate(self.clips):
            row = index // CLIP_COLUMNS
            col = index % CLIP_COLUMNS
            x = 12 + col * (card_w + gap_x)
            y = 12 + row * (card_h + gap_y)
            self.render_clip_card(index, clip, NSMakeRect(x, y, card_w, card_h))
            thread = threading.Thread(target=self.thumbnail_worker, args=(generation, index, clip), daemon=True)
            thread.start()

    @objc.python_method
    def render_clip_card(self, index: int, clip: ClipSegment, frame) -> None:
        card = glass_view(frame, 18, COLORS["card"])
        image_view = NSImageView.alloc().initWithFrame_(NSMakeRect(10, 10, 274, 154))
        image_view.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        image_view.setEditable_(False)
        set_layer(image_view, 14, COLORS["field"], ns_color("#FFFFFF", 0.18))
        card.addSubview_(image_view)
        self.thumbnail_views[index] = image_view

        play = button(self.text("play"), NSMakeRect(105, 70, 84, 34), self, "playLowPreview:", "secondary")
        play.setTag_(index)
        card.addSubview_(play)

        title = label(f"Highlight #{index + 1:03d}", NSMakeRect(12, 176, 180, 22), 13, 0.28)
        card.addSubview_(title)
        meta = label(
            self.text("clip_info", kills=clip.kills, duration=clip.duration, start=clip.start, end=clip.end),
            NSMakeRect(12, 198, 250, 42),
            13,
            0.0,
            COLORS["muted"],
        )
        card.addSubview_(meta)
        high = button(self.text("play_high"), NSMakeRect(12, 244, 82, 30), self, "playHigh:", "secondary")
        reveal = button(self.text("reveal"), NSMakeRect(102, 244, 74, 30), self, "revealClip:", "secondary")
        delete = button(self.text("delete"), NSMakeRect(184, 244, 74, 30), self, "deleteClip:", "danger")
        for item in (high, reveal, delete):
            item.setTag_(index)
            card.addSubview_(item)
        self.play_buttons[index] = high
        self.clips_content.addSubview_(card)

    @objc.python_method
    def select_clip(self, index: int) -> None:
        if 0 <= index < len(self.clips):
            self.selected_clip_index = index

    @objc.python_method
    def thumbnail_worker(self, generation: int, index: int, clip: ClipSegment) -> None:
        try:
            seek = self.preview_cache.thumbnail_seek_seconds(clip, float(str(self.before_field.stringValue())))
            path = self.preview_cache.thumbnail_for(clip, seek)
            self.events.put(("thumbnail_ready", (generation, index, path)))
        except Exception:
            self.events.put(("thumbnail_error", (generation, index)))

    @objc.python_method
    def handle_thumbnail_ready(self, generation: int, index: int, image_path: Path) -> None:
        if generation != self.thumbnail_generation or index not in self.thumbnail_views:
            return
        image = NSImage.alloc().initWithContentsOfFile_(str(image_path))
        if image is not None:
            self.thumbnail_views[index].setImage_(image)
            self.thumbnail_paths[index] = image_path

    @objc.python_method
    def handle_thumbnail_error(self, generation: int, index: int) -> None:
        if generation != self.thumbnail_generation or index not in self.thumbnail_views:
            return
        self.thumbnail_views[index].setToolTip_(self.text("thumbnail_failed"))

    def playLowPreview_(self, sender) -> None:
        index = int(sender.tag())
        if index < 0 or index >= len(self.clips):
            return
        if self.playing_clip_index == index and self.playing_mode == "card":
            self.stop_preview()
            return
        self.stop_preview()
        self.select_clip(index)
        self.preview_play_token += 1
        token = self.preview_play_token
        self.playing_clip_index = index
        self.playing_mode = "card"
        self.set_status("preview_generating")
        threading.Thread(target=self.card_preview_worker, args=(token, index, self.clips[index]), daemon=True).start()

    @objc.python_method
    def card_preview_worker(self, token: int, index: int, clip: ClipSegment) -> None:
        try:
            frames = self.preview_cache.card_preview_frames_for(clip)
            self.events.put(("card_preview_ready", (token, index, frames)))
        except Exception as exc:
            self.events.put(("card_preview_error", (token, self.text("preview_failed") + f": {exc}")))

    @objc.python_method
    def handle_card_preview_ready(self, token: int, index: int, frames: list[Path]) -> None:
        if token != self.preview_play_token or index not in self.thumbnail_views:
            return
        images = []
        for frame in frames:
            image = NSImage.alloc().initWithContentsOfFile_(str(frame))
            if image is not None:
                images.append(image)
        if not images:
            self.handle_card_preview_error(token, self.text("preview_no_frames"))
            return
        self.preview_frames = images
        self.preview_frame_index = 0
        self.set_status("low_preview")
        self.preview_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1 / CARD_PREVIEW_FPS,
            self,
            NSSelectorFromString("advancePreview:"),
            None,
            True,
        )

    @objc.python_method
    def handle_card_preview_error(self, token: int, message: str) -> None:
        if token != self.preview_play_token:
            return
        self.stop_preview()
        self.set_status("preview_failed")
        self.show_alert(message)

    def advancePreview_(self, _timer) -> None:
        if self.playing_clip_index is None or self.playing_mode != "card":
            self.stop_preview()
            return
        view = self.thumbnail_views.get(self.playing_clip_index)
        if view is None or self.preview_frame_index >= len(self.preview_frames):
            self.stop_preview()
            self.set_status("done")
            return
        view.setImage_(self.preview_frames[self.preview_frame_index])
        self.preview_frame_index += 1

    @objc.python_method
    def stop_preview(self) -> None:
        self.preview_play_token += 1
        if self.preview_timer is not None:
            self.preview_timer.invalidate()
            self.preview_timer = None
        if self.playing_clip_index is not None and self.playing_mode == "card":
            image_path = self.thumbnail_paths.get(self.playing_clip_index)
            view = self.thumbnail_views.get(self.playing_clip_index)
            if image_path and view is not None:
                view.setImage_(NSImage.alloc().initWithContentsOfFile_(str(image_path)))
        if self.player_process and self.player_process.poll() is None:
            self.player_process.terminate()
        if self.playing_clip_index is not None and self.playing_mode == "high":
            self.set_high_button_title(self.playing_clip_index, self.text("play_high"))
        self.player_process = None
        self.preview_frames = []
        self.preview_frame_index = 0
        self.playing_clip_index = None
        self.playing_mode = None

    def playHigh_(self, sender) -> None:
        index = int(sender.tag())
        if index < 0 or index >= len(self.clips):
            return
        if self.playing_clip_index == index and self.playing_mode == "high":
            self.stop_preview()
            return
        self.stop_preview()
        ffplay = resolve_tool("ffplay")
        if not ffplay:
            self.show_alert(self.text("missing_ffplay"))
            return
        clip = self.clips[index]
        self.player_process = subprocess.Popen(
            [ffplay, "-autoexit", "-window_title", clip.name, str(Path(clip.path))],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **hidden_subprocess_kwargs(),
        )
        self.playing_clip_index = index
        self.playing_mode = "high"
        self.set_high_button_title(index, self.text("stop_play"))
        self.set_status("high_playing")
        threading.Thread(target=self.player_watch_worker, daemon=True).start()

    @objc.python_method
    def player_watch_worker(self) -> None:
        process = self.player_process
        if process is not None:
            process.wait()
        self.events.put(("player_done", None))

    @objc.python_method
    def handle_player_done(self) -> None:
        if self.playing_clip_index is not None and self.playing_mode == "high":
            self.set_high_button_title(self.playing_clip_index, self.text("play_high"))
        self.player_process = None
        if self.playing_mode == "high":
            self.playing_clip_index = None
            self.playing_mode = None
            self.set_status("done")

    @objc.python_method
    def set_high_button_title(self, index: int, title: str) -> None:
        item = self.play_buttons.get(index)
        if item is not None:
            item.setAttributedTitle_(attributed_title(title, COLORS["text"], 13, 0.28))

    def revealClip_(self, sender) -> None:
        clip = self.clip_from_sender(sender)
        if clip is None:
            return
        subprocess.Popen(["open", "-R", str(Path(clip.path))])

    def deleteClip_(self, sender) -> None:
        index = int(sender.tag())
        if index < 0 or index >= len(self.clips):
            return
        clip = self.clips[index]
        if not self.confirm(self.text("delete_confirm", kills=clip.kills, start=clip.start, end=clip.end)):
            return
        self.stop_preview()
        path = Path(clip.path)
        try:
            if path.exists():
                path.unlink()
        except Exception as exc:
            self.show_alert(self.text("delete_failed", error=exc))
            return
        self.append_log(self.text("deleted_log", name=path.name))
        self.clips.pop(index)
        self.refresh_clip_cards()

    @objc.python_method
    def clip_from_sender(self, sender) -> ClipSegment | None:
        index = int(sender.tag())
        if 0 <= index < len(self.clips):
            return self.clips[index]
        return None

    @objc.python_method
    def show_alert(self, message: str) -> None:
        alert = NSAlert.alloc().init()
        alert.setMessageText_(self.text("app_title"))
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_("OK")
        alert.runModal()

    @objc.python_method
    def confirm(self, message: str) -> bool:
        alert = NSAlert.alloc().init()
        alert.setMessageText_(self.text("app_title"))
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_(self.text("confirm"))
        alert.addButtonWithTitle_(self.text("cancel"))
        return alert.runModal() == NSAlertFirstButtonReturn


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, _notification) -> None:
        self.controller = MacClipperController.alloc().init()
        self.controller.show()

    def applicationShouldTerminateAfterLastWindowClosed_(self, _sender) -> bool:
        return True


def main() -> None:
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
