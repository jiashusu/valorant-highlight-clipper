# 开发日志

## 2026-05-13

### 更新记录：macOS AppKit UI 二次深度优化

- 需求来源：
  - 用户反馈启动后右上角“检查更新”默认出现蓝色焦点框。
  - 当前底色仍偏深蓝，希望改成更接近 Apple 黑的暗色。
  - 输入框和按钮里的文字视觉偏上，需要更居中。
  - Windows v1.3.2 右上角新增了作者链接和中英文切换，macOS 需要参考同步。
- 本次修改：
  - 所有自绘胶囊按钮和输入框关闭 AppKit focus ring，启动后清空默认 first responder，避免右上角默认蓝框。
  - 背景、面板、输入框、日志、表格和卡片从黑蓝系调整为 neutral Apple 黑灰系，只保留青色作为主操作强调色。
  - 新增居中文本 cell，让单行输入框文字在圆角框内更接近垂直居中。
  - 顶部右侧新增 `原作者: shu` 链接，点击打开 mac 主仓库。
  - 顶部右侧新增 `EN / 中文` 切换按钮，默认中文，不持久化语言选择。
  - macOS AppKit 文案整理为中英文 `TEXTS` 表，主要标题、按钮、状态、提示、弹窗和卡片操作支持切换。
  - Highlights 空状态卡片改得更轻、更居中，边框和背景层级继续降低硬边框感。
- Windows 同步提示：
  - Windows 端当前正在更新 UI，本次 macOS 只同步 v1.3.2 已确认的右上角作者链接和语言切换逻辑，不改 Windows 仓库。

### 更新记录：macOS 原生 AppKit 玻璃风 UI 重做

- 需求来源：
  - 用户反馈当前 Tkinter 界面按钮、线条和排版仍然很旧，希望改成暗色、圆润、玻璃感更强的 Apple 风。
- 本次修改：
  - 新增 `src/valorant_clipper/mac_app.py`，使用原生 macOS AppKit / PyObjC 构建主界面。
  - `mac/launcher.py` 改为启动 AppKit 版，旧 `desktop_app.py` 保留为历史 fallback，不再作为 macOS 打包入口。
  - 新增 `src/valorant_clipper/preview_cache.py`，把缩略图和卡片低清预览帧缓存从 Tkinter UI 中抽离。
  - `requirements.txt` 增加 `pyobjc-framework-Cocoa`，`mac/ValorantHighlightClipper.spec` 增加 AppKit/PyObjC hidden imports，并移除 Tkinter/ImageTk 入口依赖。
  - 主界面改为深黑蓝渐变背景、半透明玻璃面板、圆角输入框、胶囊按钮和低对比边线。
  - Highlights 区保留三列卡片墙：卡片内可直接播放低清预览，旁边保留高清播放、Finder 定位和删除功能。
  - 文件夹、视频、输出目录选择改用原生 `NSOpenPanel`。
  - 更新检查、开发日志、ffmpeg/ffprobe/ffplay、剪辑核心和队友击杀过滤逻辑保持不变。
- Windows 同步提示：
  - Windows 端可以继续保留现有实现；如需同步视觉，可参考本次 AppKit 版的卡片层级、圆角尺寸、按钮状态和预览缓存模块。

## 2026-05-12

### 调整记录：移除顶部青色同步横幅

- 用户反馈：
  - 顶部青色同步横幅太显眼，希望去掉。
- 本次修改：
  - 移除顶部 `已同步 Windows v1.3.2 · 384x216 预览 · Finder 精确定位` 横幅。
  - 保留标题旁的 `macOS v1.3.2 · 构建号`，仍然可以确认当前运行版本。

### 修复记录：本地 release App 没显示最新版界面

- 问题现象：
  - GitHub 源码已经包含 `macOS v1.3.2`、同步标识和新的 Highlights 空状态。
  - 用户实际打开的 release App 仍然显示旧界面，没有版本号和同步条。
- 根因：
  - 本地打包目录 `无畏契约自动剪辑/src/valorant_clipper/desktop_app.py` 没有被最新源码覆盖。
  - `build_info.py` 已经是新版本号，但桌面 UI 源码仍是旧文件，所以打包出的 `.app` 看不到新界面。
- 本次处理：
  - 强制重新同步 mac 源码到本地打包目录。
  - 重新写入 `BUILD_SHA = "880a187"`。
  - 在打包目录直接运行自检，确认能读到 `macOS v1.3.2`、`880a187` 和同步标识。
  - 重新执行 PyInstaller 打包并准备覆盖 release `.app` 和 zip。

### 更新记录：让 macOS 更新变得一眼可见

- 需求来源：
  - 用户反馈“看不出来有更新”，截图显示新参数虽然存在，但界面变化不明显。
  - 截图中 Highlights 空区域仍显示大块空白和突兀滚动条，视觉上像旧版。
- 本次修改：
  - 顶部新增 `macOS v1.3.2` 与当前构建短版本号。
  - 顶部新增醒目的同步标识：`已同步 Windows v1.3.2 · 384x216 预览 · Finder 精确定位`。
  - Highlights 没有片段时隐藏右侧滚动条，避免空页面出现大白色滚动条。
  - 空状态从一行灰字改成深色提示卡片：
    - 未剪辑时提示剪辑后会显示低清预览、约几杀、高清播放、定位视频和删除按钮。
    - 没有导出片段时提示可以调整置信度、最短事件秒数或严格过滤。
- Windows 同步提示：
  - Windows 端可以保留自绘标题栏，同时也建议增加版本号和同步标识，方便确认当前运行的 exe 是否为最新版。

### 更新记录：继续参考 Windows v1.3.2 同步 macOS 体验

- 需求来源：
  - 用户要求继续查看 `jiashusu/valorant-highlight-clipper-windows` 并同步更新。
  - Windows 仓库只作为参考，不向 Windows 仓库写入任何内容。
- 已参考的 Windows 更新：
  - `v1.3.1-windows`：更大窗口、更宽右侧预览区、更清晰卡片预览、文件定位修复。
  - `v1.3.2-windows`：定位导出 mp4 更严格、Highlights 提示条、深色 UI 细节优化。
- 本次 macOS 修改：
  - 默认窗口从 `1560x960` 提升到 `1720x980`，最小窗口提升到 `1360x840`。
  - 左右分栏权重从 `2:3` 调整为 `2:6`，右侧 Highlights 卡片墙获得更多空间。
  - 缩略图和卡片内低清预览从 `320x180` 提升到 `384x216`，继续保持 `30fps`、Lanczos 缩放和较高 JPEG 质量。
  - “定位此视频”改成更严格的导出片段定位逻辑：
    - 导出 mp4 存在时，macOS Finder 直接选中该文件。
    - 导出 mp4 不存在时，弹窗显示真实路径，并写入处理日志。
  - Highlights 标题下新增黄色提示条，提醒当前版本仍可能输出队友击杀片段，可以先手动删除。
  - 深色 UI 继续优化：去掉明显复古边框，滚动条、危险按钮和提示条颜色同步 Windows 版风格。
- 保留 macOS 差异：
  - 不照搬 Windows 黑色自绘标题栏，macOS 仍保留系统原生红黄绿窗口按钮。
  - 更新检查继续指向 macOS 主仓库和 macOS Actions，不切到 Windows Release。

## 2026-05-11

### 更新记录：参考 Windows 新仓库同步 macOS 优化

- 需求来源：
  - Windows 新仓库 `jiashusu/valorant-highlight-clipper-windows` 已经有一批新体验，需要同步回 macOS 版。
  - Windows 仓库只作为参考，不向 Windows 仓库写入任何内容。
- 本次修改：
  - 默认窗口改为 `1560x960`，最小窗口改为 `1280x820`。
  - 同步深色 UI 风格：深色背景、面板、卡片、输入框、日志、表格和进度条。
  - 默认置信度提升到 `0.93`，最短事件秒数提升到 `0.75`。
  - 严格过滤队友击杀时，核心识别至少使用 `0.94` 置信度和 `0.75s` 最短事件。
  - 导出画质提升为 H.264 `slow` preset、`CRF 14`、`yuv420p`，音频优先复制原音轨，失败时回退 AAC 192k。
  - 卡片缩略图和卡片内预览从 `260x146 / 20fps` 提升到 `320x180 / 30fps`，缩放改用 Lanczos，JPEG 质量提升。
  - “打开目录”改成“定位此视频”，macOS 下使用 Finder 直接选中导出的 mp4。
  - 扫描完成后自动选中第一个视频；开始剪辑时如果列表里已有视频也会自动补选。
  - 处理日志改为只读，程序仍可写入进度日志。
  - Highlights 卡片区支持鼠标滚轮滚动，鼠标放在卡片、缩略图或按钮上也能滚动。
- 保留 macOS 差异：
  - 更新检查仍指向 macOS 主仓库和 macOS Actions，不切到 Windows Release。

### 更新记录：低清预览改为卡片内播放

- 需求来源：
  - 缩略图播放三角应该在当前卡片红框区域内预览，不应该另开播放器窗口。
- 本次修改：
  - 点击缩略图后，低清预览直接在该卡片的缩略图区域内播放。
  - 低清预览改为缓存 260x146、20fps 的轻量帧序列，只播放当前选中的一张卡片。
  - 预览帧会先缓存再预加载到内存，播放时只切换当前卡片图片，减少卡顿。
  - 播放结束或再次点击会恢复原缩略图和播放三角。
  - “高清播放”按钮继续另开内建播放器播放原始高清 mp4。
- Windows 同步提示：
  - Windows 端如果还用 Tkinter，可以同样只给当前卡片加载低清帧序列，不要给全部卡片同时播放。
  - 高清播放仍可保留 `ffplay.exe` 外部播放器方案。

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
