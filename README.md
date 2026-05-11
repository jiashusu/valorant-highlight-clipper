# Valorant 高光剪辑纯桌面版

这是纯桌面应用版本，不打开浏览器，不启动本地网页服务。所有操作都在应用窗口里完成。

## 功能

- 选择素材文件夹或单个视频
- 扫描视频列表
- 设置识别参数
- 后台剪辑并显示进度日志
- 显示每个导出片段的估算击杀数
- 打开输出目录或选中片段所在目录

## macOS 打包

```bash
./mac/build_mac.sh
```

产物：

```text
dist/ValorantHighlightClipper.app
```

macOS 打包时会把当前系统可用的 `ffmpeg` 和 `ffprobe` 放进 `.app`。

## Windows 打包

在 Windows 上运行：

```powershell
powershell -ExecutionPolicy Bypass -File windows\build_windows.ps1
```

产物：

```text
dist\ValorantHighlightClipper.exe
```

Windows 打包脚本会自动下载并内置 `ffmpeg.exe` 和 `ffprobe.exe`。
