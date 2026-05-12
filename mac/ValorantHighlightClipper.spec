# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from shutil import which


project = Path.cwd()

datas = [
    (str(project / "assets" / "valorant_clipper"), "assets/valorant_clipper"),
]
binaries = []

for tool in ("ffmpeg", "ffprobe", "ffplay"):
    tool_path = which(tool)
    if tool_path:
        binaries.append((tool_path, "ffmpeg"))

a = Analysis(
    [str(project / "mac" / "launcher.py")],
    pathex=[str(project / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=["tkinter", "tkinter.filedialog", "PIL.ImageTk", "numpy.core.multiarray"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["fastapi", "uvicorn", "starlette", "pydantic"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ValorantHighlightClipper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ValorantHighlightClipper",
)
app = BUNDLE(
    coll,
    name="ValorantHighlightClipper.app",
    icon=None,
    bundle_identifier="com.jiashusu.valorant-highlight-clipper",
)
