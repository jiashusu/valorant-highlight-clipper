# Valorant 高光剪辑 macOS 纯桌面版

这是 macOS 纯桌面应用版本，不打开浏览器，不启动本地网页服务。所有操作都在应用窗口里完成。

## 功能

- 选择素材文件夹或单个视频
- 扫描视频列表
- 设置识别参数
- 后台剪辑并显示进度日志
- 显示每个导出片段的估算击杀数
- 3 列 Highlights 卡片墙，支持低清卡片内预览、高清播放、定位视频和删除片段
- 打开输出目录或在 Finder 中精确选中导出的片段
- 自动检查 GitHub 上的 macOS 新版本

## 打包

```bash
./mac/build_mac.sh
```

产物：

```text
dist/ValorantHighlightClipper.app
```

macOS 打包时会把当前系统可用的 `ffmpeg`、`ffprobe` 和 `ffplay` 放进 `.app`。
