# 开发日志

## 2026-05-11

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

### 后续建议

- 如果继续只做 macOS，建议删除旧网页版本文件和旧控制脚本，进一步瘦身项目。
- 如果之后重新做 Windows，建议在 Windows 环境中单独建项目或分支，不再混在 macOS release 目录里。
- 如果要发给别人使用，建议后续做代码签名和 notarization，减少 macOS Gatekeeper 拦截。
