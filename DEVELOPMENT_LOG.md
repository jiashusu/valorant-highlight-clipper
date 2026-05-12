# 开发日志

## 2026-05-11

### 更新记录：缩略图播放改为低清预览视频

- 需求来源：
  - 希望点击高光缩略图中间的播放按钮时播放预览版，而不是直接打开高清版。
  - 希望低清预览比之前图片序列更顺一些。
- 本次修改：
  - 点击缩略图播放三角时，先生成并播放低清预览 mp4。
  - 低清预览使用 `ffmpeg` 生成 960 宽、30fps、H.264 的缓存视频，比图片序列更流畅。
  - 低清预览第一次点击会生成缓存，后续重复播放同一片段会直接复用。
  - 底部“高清播放”按钮保留原功能，仍然直接播放原始导出 mp4。
  - 播放高清时会取消未完成的低清预览生成请求，避免误打开旧预览。
- Windows 同步提示：
  - Windows 端同样可以缓存一份 `preview.mp4`，缩略图播放走预览版，高清按钮走原片。
  - 建议缓存 key 包含源文件路径、大小、修改时间、预览宽度和压缩参数。

### 更新记录：导出区改为 Valorant Tracker 风格高光网格

- 需求来源：
  - 希望导出片段区域更接近 Valorant Tracker 的 Highlights 页面。
  - 希望多个片段可以像高光墙一样排列，而不是一条一条竖向列表。
- 本次修改：
  - 导出区卡片从竖向列表改为 3 列网格布局。
  - 每张低清缩略图中央增加播放三角标识。
  - 卡片标题改为 `Highlight #序号`。
  - 卡片信息只保留约几杀、片段长度、起止时间，不显示文件名。
  - 操作按钮改为卡片底部横向排列：高清播放、打开目录、删除。
  - 双击缩略图也可以直接高清播放。
- Windows 同步提示：
  - Windows 端同步时重点复刻 3 列网格、缩略图播放标识和卡片底部操作按钮。
  - 仍然建议保留 `ffmpeg` 缩略图缓存和 `ffplay` 高清播放方案。

### 更新记录：导出区改为低清预览卡片

- 需求来源：
  - “片段预览”和“导出片段”分开显示占空间，而且表格里文件路径太长。
  - 希望每个片段先看到低画质击杀画面，需要时再用内建播放器看高清版。
- 本次修改：
  - 右侧导出区从“单独预览框 + 表格”改成可滚动的片段卡片列表。
  - 每个片段卡片显示一张低清击杀画面缩略图。
  - 每个片段卡片下方只显示“约 N 杀”、开始时间、结束时间和长度，不再显示文件名或完整路径。
  - 每个片段卡片旁边提供“高清播放”“打开目录”“删除”按钮。
  - 低清缩略图由 `ffmpeg` 后台生成并缓存，不阻塞主界面。
  - “高清播放”继续调用内建 `ffplay` 播放真实 mp4。
- Windows 同步提示：
  - Windows 端可复用同样结构：缩略图用 `ffmpeg.exe` 生成，高清播放用 `ffplay.exe`。
  - 缩略图生成不要直接在 UI 线程运行，避免列表卡顿。

### 更新记录：片段预览改为内建播放器播放真实视频

- 需求来源：
  - 图片序列预览虽然比之前顺一些，但本质还是模拟播放，不如直接播放真实 mp4。
  - 希望用电脑本身的播放性能来减少卡顿和掉帧。
- 本次修改：
  - 移除 App 内预览的抽帧、JPG 缓存、`ImageTk` 图片序列播放逻辑。
  - 点击“播放”时改为启动随 App 打包的 `ffplay` 内建播放器，直接播放选中的导出 mp4。
  - “播放”按钮在播放时变为“停止播放”，可从主 App 里结束当前片段播放。
  - 选择不同片段时会自动停止上一段播放。
  - PyInstaller 打包配置增加 `ffplay`，确保 macOS `.app` 自带播放器。
- Windows 同步提示：
  - Windows 端建议同样打包 `ffplay.exe`，播放按钮直接调用真实 mp4。
  - 如果 Windows 后续使用 Qt/Electron，也可以改为系统播放器组件，但不要再走逐帧图片播放。

### 更新记录：优化 App 内预览播放流畅度

- 需求来源：
  - App 内片段预览已经能播放，但播放时明显卡顿、掉帧。
- 问题原因：
  - 旧实现是在播放过程中每一帧都从磁盘读取 JPG，再交给 Tkinter 转成可显示图片。
  - 这个过程会卡住 UI 主线程，所以视频越长、磁盘越忙，越容易掉帧。
- 本次修改：
  - 选中片段后仍用 `ffmpeg` 生成轻量预览帧。
  - 预览开始前，把全部预览帧一次性转换成内存里的 `ImageTk.PhotoImage`。
  - 播放时只切换内存图片，不再边播边读磁盘。
  - 预览帧率从 12fps 提升到 18fps，让动作看起来更接近网页版本。
  - 预览缓存 key 加入帧率和宽度，避免旧缓存影响新播放效果。
- Windows 同步提示：
  - Windows 端如果使用 Tkinter，同样建议先把预览帧预加载为 `PhotoImage`，不要播放时再打开图片文件。
  - 如果之后改成 Qt / Electron，可优先使用系统视频播放器组件，效果会比 Tkinter 图片序列更好。

### 更新记录：导出区增加 App 内视频预览、删除和击杀标识

- 需求来源：
  - 导出区原来只有表格，不像网页版本那样能直接查看片段。
  - 希望导出的 clip 可以在 App 内直接播放。
  - 希望每个片段有删除选项。
  - 希望明显显示“约 N 杀”的标识。
- 本次修改：
  - 右侧导出区新增“片段预览”区域。
  - 选择导出片段后，App 会用内置 `ffmpeg` 生成轻量预览帧，并在窗口内播放，不打开浏览器。
  - 新增播放/暂停按钮。
  - 新增“删除片段”按钮，会删除磁盘上的导出 mp4，并同步移除列表项。
  - 新增“约 N 杀”标识，选中片段时在预览区顶部展示。
  - 导出列表中的击杀列从数字改为 `约 N 杀`。
  - PyInstaller hidden import 增加 `PIL.ImageTk`，确保打包后预览图片渲染模块可用。
- Windows 同步提示：
  - Windows 端如果继续使用 Tkinter，可复用同样思路：用 ffmpeg 将选中 clip 转为预览帧，再用 `PIL.ImageTk.PhotoImage` 播放。
  - Windows 打包时也需要包含 `PIL.ImageTk` hidden import。

### 更新记录：修复 macOS 剪辑时报 `numpy.core.multiarray` 缺失

- 问题现象：
  - macOS App 可以打开，也可以扫描视频。
  - 点击开始剪辑后报错：`No module named 'numpy.core.multiarray'`。
- 根因判断：
  - 当前本地打包环境安装了 NumPy 2.x。
  - 项目里的模型文件 `valorant.npy` 来自旧版 NumPy 序列化格式，运行时会引用 `numpy.core.multiarray`。
  - PyInstaller 打包时也可能因为这是 pickle 间接引用而没有自动收进去。
- 本次修改：
  - 将 `requirements.txt` 中 NumPy 固定为 `numpy>=1.26.0,<2.0`。
  - 在 `mac/ValorantHighlightClipper.spec` 里显式加入 hidden import：`numpy.core.multiarray`。
  - 后续重新打包 macOS App，确保 App 内置兼容版本的 NumPy。
- Windows 同步提示：
  - Windows 端重建时同样建议使用 `numpy>=1.26.0,<2.0`。
  - 如果用 PyInstaller，也建议加入 hidden import：`numpy.core.multiarray`。

### 项目目标

为 VALORANT 录屏制作本地高光剪辑工具。核心目标是自动识别击杀信息，导出高光片段，并尽量减少队友击杀被误剪的问题。

### 已完成

- 分析原始剪辑素材和检测逻辑，整理为独立 Python 项目。
- 实现核心剪辑流程：
  - 扫描视频文件。
  - 使用 `ffprobe` 获取视频信息。
  - 使用 `ffmpeg` 抽取击杀信息区域帧。
  - 使用随项目打包的 `valorant.npy` 和 `valorant-mask.png` 做击杀识别。
  - 合并相邻击杀事件并导出片段。
- 增加每个导出片段的估算击杀数。
- 增加严格过滤参数，降低队友击杀被误识别的概率。
- 做过网页版本和本地控制脚本验证。
- 后续根据使用反馈转为纯桌面版：
  - 不打开浏览器。
  - 不启动本地网页服务。
  - 所有路径选择、扫描、参数设置、进度日志、导出列表都在 App 窗口内完成。
- 构建 macOS `.app`：
  - 入口：`mac/launcher.py`
  - 打包脚本：`mac/build_mac.sh`
  - PyInstaller 配置：`mac/ValorantHighlightClipper.spec`
  - 打包时包含模型资源和 `ffmpeg/ffprobe`。
- 修复 macOS 双击闪退问题：
  - 原因：桌面 GUI 中导出片段表格的 `path` 列少了宽度配置，启动时报 `ValueError`。
  - 修复：补齐 `("path", "文件", 360)`。
- 删除 Windows 相关内容，保留 macOS 项目方向。
- 增加更新检查功能：
  - App 启动后自动检查一次更新。
  - App 运行期间每 30 分钟后台检查一次。
  - 标题栏提供“检查更新”按钮。
  - 优先使用 GitHub API；私有仓库不可访问时，回退到本机已登录的 `gh` CLI。
  - 发现远端 `main` 提交比当前 App 打包提交更新时，弹窗提示并可打开 GitHub Actions 下载新版 macOS App。

### 当前目录定位

- `valorant-highlight-clipper-release`：主源码仓库，用于继续开发和推送 GitHub。
- `无畏契约自动剪辑/release/pure-app/mac`：当前 macOS 可用产物目录。

### 当前 macOS 产物

```text
/Users/jiashusu/Documents/jiashu project/无畏契约自动剪辑/release/pure-app/mac/ValorantHighlightClipper.app
/Users/jiashusu/Documents/jiashu project/无畏契约自动剪辑/release/pure-app/mac/ValorantHighlightClipper-macOS.zip
```

### 验证记录

- 单元测试通过：`4 passed`
- macOS `.app` 命令行启动验证通过，不再出现启动即崩溃。
- GitHub macOS 构建 workflow 可用。
- 更新检查依赖当前机器可访问 GitHub；由于仓库是 private，未登录 `gh` 时会检查失败。

### 后续建议

- 如果继续只做 macOS，建议删除旧网页版本文件和旧控制脚本，进一步瘦身项目。
- 如果之后重新做 Windows，建议在 Windows 环境中单独建项目或分支，不再混在 macOS release 目录里。
- 如果要发给别人使用，建议后续做代码签名和 notarization，减少 macOS Gatekeeper 拦截。
