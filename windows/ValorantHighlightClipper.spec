# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


project = Path.cwd()

datas = [
    (str(project / "assets" / "valorant_clipper"), "assets/valorant_clipper"),
    (str(project / "static" / "valorant_clipper"), "static/valorant_clipper"),
]

ffmpeg_dir = project / "vendor" / "ffmpeg"
for binary_name in ("ffmpeg.exe", "ffprobe.exe"):
    binary_path = ffmpeg_dir / binary_name
    if binary_path.exists():
        datas.append((str(binary_path), "ffmpeg"))

a = Analysis(
    [str(project / "windows" / "launcher.py")],
    pathex=[str(project / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=["tkinter", "tkinter.filedialog"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ValorantHighlightClipper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
