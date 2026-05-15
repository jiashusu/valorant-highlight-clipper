# Valorant Highlight Clipper for macOS

一款本地运行的 macOS 原生桌面 App，用来扫描 VALORANT 录屏、识别击杀信息区域，并自动导出高光片段。

This is a native macOS desktop app that scans VALORANT recordings, detects kill-feed events, and exports highlight clips locally.

> 非 Riot Games 官方项目。本工具只处理你本机的视频文件，不接入 Riot API，也不会修改游戏文件。
>
> This is not an official Riot Games project. It only processes local video files, does not use the Riot API, and does not modify game files.

## 中文说明

### 项目定位

`Valorant Highlight Clipper` 是给 macOS 用户使用的 VALORANT 高光剪辑工具。它会读取录屏中的击杀信息区域，按参数识别击杀事件，把前后几秒自动合并并导出为独立 mp4 片段。

它是纯桌面版：不打开浏览器，不启动本地网页服务，所有路径选择、扫描、剪辑、预览、删除和更新检查都在 App 窗口里完成。

### 相关版本

- Windows 版仓库：[jiashusu/valorant-highlight-clipper-windows](https://github.com/jiashusu/valorant-highlight-clipper-windows)
- 如果你在 Windows 上使用，请下载 Windows 版；它使用 PySide6 桌面界面、Windows 专用打包脚本和 exe 发布流程。
- 本仓库只维护 macOS AppKit 版本。两个版本会尽量同步核心剪辑体验，但 UI、打包方式和更新检查入口会按系统分别维护。

### 功能亮点

- 原生 macOS AppKit 桌面界面，暗色 Apple 黑灰玻璃风。
- 支持选择素材文件夹或单个视频文件。
- 支持递归扫描素材目录。
- 自动读取视频时长、大小和路径。
- 自动识别击杀信息区域并导出高光片段。
- 每个导出片段显示约几杀、起止时间和片段长度。
- Highlights 三列卡片墙，适合快速筛选片段。
- 卡片内低清预览，不必每次打开完整播放器。
- 高清播放按钮调用内建 `ffplay` 播放真实导出视频。
- Finder 精确定位导出的 mp4 文件。
- 支持删除误剪或不需要的片段。
- 严格过滤队友击杀选项，尽量降低误剪。
- 开始剪辑前显示粗略预计耗时。
- 中英文界面切换，默认中文。
- 自动检查 GitHub 上的 macOS 新版本。
- `.app` 内可打包 `ffmpeg`、`ffprobe`、`ffplay` 和识别模型资源。

### 截图

截图后续补充。当前界面是 macOS 原生 AppKit 暗色玻璃风：左侧为路径、参数和视频列表，右侧为处理日志和 Highlights 卡片墙。

### 下载和使用

1. 在 GitHub Releases 或 Actions 产物中下载最新版 macOS App。
2. 解压后打开 `ValorantHighlightClipper.app`。
3. 准备你的录屏目录，默认建议放在：

```text
~/Movies/VALORANT_CLIPS
```

4. 在 App 中选择素材文件夹或单个视频。
5. 选择输出目录，默认会输出到 App 运行目录下的：

```text
outputs/valorant_highlights
```

6. 点击“扫描视频”，确认列表里出现视频。
7. 点击“开始剪辑”，等待导出完成。
8. 在 Highlights 卡片墙中预览、高清播放、定位或删除片段。

### 参数建议

默认参数已经按当前测试视频调过，一般不建议随便改。特别是这些参数：

- `置信度`：越高越严格，误剪更少，但可能漏掉击杀。
- `识别帧率`：越高越细，但处理更慢。
- `提前秒数 / 延后秒数`：控制导出片段前后保留多久。
- `合并间隔`：相近击杀会合并到同一个片段。
- `最短事件秒`：过滤很短的误识别。
- `严格过滤队友击杀`：推荐开启。
- `快速无损截取`：速度更快，但兼容性和切点精度可能受视频编码影响。

### 从源码运行

环境要求：

- macOS
- Python 3.11 或 3.12
- `ffmpeg`
- `ffprobe`
- `ffplay`

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

运行 AppKit 桌面版：

```bash
PYTHONPATH=src python3 mac/launcher.py
```

如果你的素材目录不在默认位置，可以设置环境变量：

```bash
export VALORANT_CLIPS_DIR="/path/to/your/VALORANT_CLIPS"
PYTHONPATH=src python3 mac/launcher.py
```

### 打包 macOS App

先确认 `ffmpeg`、`ffprobe`、`ffplay` 可以在当前系统 PATH 中找到。打包脚本会把它们一起放进 `.app`：

```bash
./mac/build_mac.sh
```

构建完成后产物位于：

```text
dist/ValorantHighlightClipper.app
```

打包时会写入当前 Git 提交作为构建号，App 顶部会显示类似：

```text
macOS v1.3.2 · 0a2fcf0
```

### 项目结构

```text
src/valorant_clipper/core.py          核心识别、分组和导出逻辑
src/valorant_clipper/mac_app.py       macOS AppKit 桌面界面
src/valorant_clipper/preview_cache.py 缩略图和低清预览缓存
src/valorant_clipper/update_checker.py 更新检查
assets/valorant_clipper/              击杀识别模型和遮罩资源
assets/app_icon/                      macOS App 图标资源
mac/build_mac.sh                      macOS 打包脚本
mac/ValorantHighlightClipper.spec     PyInstaller 打包配置
tests/                                核心逻辑测试
```

### 已知限制

- 当前识别逻辑仍可能误剪到队友击杀，建议开启“严格过滤队友击杀”，并在导出后手动删除不需要的片段。
- 识别区域按常见 16:9 VALORANT 录屏布局设计，非标准分辨率、裁剪画面或特殊 HUD 可能影响结果。
- 第一次生成缩略图和低清预览会占用一些时间，后续会复用缓存。
- 如果系统或 `.app` 内找不到 `ffmpeg` / `ffprobe` / `ffplay`，扫描、导出或高清播放会失败。
- 当前仓库维护 macOS 版本；Windows 版本不在本仓库维护。

### 常见问题

**为什么没有识别到片段？**

可以尝试降低置信度、缩短最短事件秒数，或确认视频中击杀信息区域没有被遮挡、裁剪或压缩得太严重。

**为什么会剪到队友击杀？**

击杀信息区域本身比较小，且不同录屏压缩质量差别很大。当前版本已经有严格过滤选项，但仍不能保证 100% 排除队友击杀。

**为什么播放高清版需要 ffplay？**

App 使用随包携带或系统 PATH 中的 `ffplay` 播放真实导出的 mp4，这样比在 UI 里手写播放器更稳定。

**更新检查去哪里下载新版？**

App 会检查 `jiashusu/valorant-highlight-clipper` 的 macOS 构建信息，发现新版时会引导打开 GitHub Actions 或相关下载页面。

## English

### Overview

`Valorant Highlight Clipper` is a local macOS desktop app for turning VALORANT recordings into highlight clips. It scans the kill-feed area in each video, detects kill events, merges nearby events, and exports short mp4 clips around those moments.

The app is fully desktop-native. It does not open a browser or start a local web server. File selection, scanning, clipping, previewing, deletion, and update checks all happen inside the app window.

### Related Version

- Windows repository: [jiashusu/valorant-highlight-clipper-windows](https://github.com/jiashusu/valorant-highlight-clipper-windows)
- If you use Windows, download the Windows version. It uses a PySide6 desktop UI, Windows-specific packaging scripts, and an exe release flow.
- This repository maintains the macOS AppKit version only. The two versions aim to share the same clipping workflow, while UI, packaging, and update checks are maintained separately for each platform.

### Features

- Native macOS AppKit UI with a dark Apple-style glass design.
- Select a source folder or a single video file.
- Optional recursive folder scanning.
- Video list with duration, size, and path.
- Kill-feed detection and automatic highlight export.
- Estimated kill count, start time, end time, and duration for each clip.
- Three-column Highlights card grid for quick review.
- Low-quality preview inside each card.
- HD playback through bundled or system `ffplay`.
- Reveal exported mp4 files directly in Finder.
- Delete unwanted clips from the app.
- Strict own-kill filtering to reduce teammate-kill false positives.
- Rough time estimate before clipping starts.
- Chinese / English UI toggle.
- Automatic macOS update checks through GitHub.
- PyInstaller packaging with `ffmpeg`, `ffprobe`, `ffplay`, model assets, and app icon resources.

### Screenshots

Screenshots coming soon. The current app uses a native dark AppKit layout: paths, settings, and video list on the left; process log and Highlights cards on the right.

### Quick Start

1. Download the latest macOS build from GitHub Releases or Actions artifacts.
2. Unzip and open `ValorantHighlightClipper.app`.
3. Prepare your recordings folder. The recommended default is:

```text
~/Movies/VALORANT_CLIPS
```

4. Choose a source folder or a single video in the app.
5. Choose an output folder. By default, clips are written under:

```text
outputs/valorant_highlights
```

6. Click `Scan Videos`.
7. Select a video and click `Start Clipping`.
8. Review the exported clips in the Highlights grid.

### Settings

The default settings are tuned for the current workflow and usually should not be changed unless you know what each option means.

- `Confidence`: Higher means stricter detection, fewer false positives, but more missed kills.
- `Scan FPS`: Higher is more detailed but slower.
- `Before / After seconds`: Extra time included before and after each detected event.
- `Merge gap`: Nearby kills are merged into one clip.
- `Min event sec`: Filters very short false detections.
- `Strict own-kill filter`: Recommended.
- `Fast stream copy`: Faster export, but exact cut accuracy and compatibility depend on the source video encoding.

### Run from Source

Requirements:

- macOS
- Python 3.11 or 3.12
- `ffmpeg`
- `ffprobe`
- `ffplay`

Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run the AppKit desktop app:

```bash
PYTHONPATH=src python3 mac/launcher.py
```

To override the default recordings folder:

```bash
export VALORANT_CLIPS_DIR="/path/to/your/VALORANT_CLIPS"
PYTHONPATH=src python3 mac/launcher.py
```

### Build the macOS App

Make sure `ffmpeg`, `ffprobe`, and `ffplay` are available in your PATH. The build script bundles them into the app when found:

```bash
./mac/build_mac.sh
```

Output:

```text
dist/ValorantHighlightClipper.app
```

The build script writes the current Git commit into the app, so the UI can show a short build identifier such as:

```text
macOS v1.3.2 · 0a2fcf0
```

### Project Layout

```text
src/valorant_clipper/core.py          Detection, grouping, and export logic
src/valorant_clipper/mac_app.py       Native macOS AppKit UI
src/valorant_clipper/preview_cache.py Thumbnail and low-preview cache
src/valorant_clipper/update_checker.py Update checker
assets/valorant_clipper/              Kill-feed model and mask assets
assets/app_icon/                      macOS app icon resources
mac/build_mac.sh                      macOS build script
mac/ValorantHighlightClipper.spec     PyInstaller spec
tests/                                Core logic tests
```

### Notes and Limitations

- The detector may still export teammate kills. Keep `Strict own-kill filter` enabled and manually delete unwanted clips after export.
- The kill-feed crop is designed around common 16:9 VALORANT recordings. Non-standard layouts, cropped videos, or heavily compressed footage may reduce accuracy.
- The first thumbnail or low-preview generation can take a moment; cached previews are reused afterward.
- Scanning, exporting, and HD playback require `ffmpeg`, `ffprobe`, and `ffplay`.
- This repository maintains the macOS version. The Windows version is not maintained here.

### Troubleshooting

**No clips were detected.**

Try lowering confidence, lowering the minimum event length, or checking whether the kill-feed area is visible and not heavily compressed.

**The app exported teammate kills.**

The kill-feed region is small and recording quality varies a lot. Strict filtering reduces false positives, but it cannot guarantee perfect results yet.

**HD playback does not start.**

Make sure `ffplay` is bundled in the app or available in your system PATH.

**Where does the update checker download from?**

The macOS app checks this repository, `jiashusu/valorant-highlight-clipper`, and opens the GitHub Actions or release-related download page when a newer build is available.

### License and Credits

This project is a personal utility built for local highlight clipping. VALORANT and Riot Games are trademarks or registered trademarks of Riot Games, Inc. This project is not affiliated with or endorsed by Riot Games.
