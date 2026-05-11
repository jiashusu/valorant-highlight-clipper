from __future__ import annotations

import sys
from pathlib import Path


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        candidates: list[Path] = []
        if hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS))  # type: ignore[attr-defined]
        executable = Path(sys.executable).resolve()
        candidates.extend(
            [
                executable.parent,
                executable.parents[1] / "Resources",
                executable.parents[1] / "Frameworks",
            ]
        )
        for candidate in candidates:
            if (candidate / "assets" / "valorant_clipper" / "valorant.npy").exists():
                return candidate
        return candidates[0]
    return Path(__file__).resolve().parents[2]


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        for parent in executable.parents:
            if parent.suffix == ".app":
                return parent.parent
        return executable.parent
    return resource_root()
