"""
執行期資源路徑工具

What:
    統一解析資料檔在原始碼模式與打包模式下的實際位置。

Why:
    桌面 app 打包後，`data/*.npz` 不再位於專案根目錄相對路徑。
    若仍直接使用字串相對路徑，查表與光譜資料會在 bundle 中失效。
"""

from __future__ import annotations

import sys
from pathlib import Path


def _candidate_roots() -> list[Path]:
    """
    What:
        回傳執行期可能的資源根目錄候選列表。

    Why:
        PyInstaller 在不同平台與模式下放置資料檔的位置不同，需要多路徑容錯。
    """
    roots: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        meipass_path = Path(meipass).resolve()
        roots.extend(
            [
                meipass_path,
                meipass_path / "Frameworks",
                meipass_path / "Resources",
            ]
        )

    executable = Path(sys.executable).resolve()
    roots.extend(
        [
            executable.parent,
            executable.parent.parent,
            executable.parent.parent / "Frameworks",
            executable.parent.parent / "Resources",
        ]
    )

    project_root = Path(__file__).resolve().parent
    roots.extend(
        [
            project_root,
            project_root / "dist" / "Phos" / "_internal",
            project_root / "dist" / "Phos.app" / "Contents" / "Frameworks",
        ]
    )

    unique_roots: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root not in seen:
            unique_roots.append(root)
            seen.add(root)
    return unique_roots


def resolve_resource_path(relative_path: str | Path) -> Path:
    """
    What:
        將相對資源路徑解析為目前執行環境中的實際檔案路徑。

    Why:
        同一段核心程式要能在 repo 內執行，也要能在 `dist/Phos.app` 中執行。
    """
    candidate = Path(relative_path)
    if candidate.is_absolute():
        return candidate

    for root in _candidate_roots():
        resolved = root / candidate
        if resolved.exists():
            return resolved

    return _candidate_roots()[0] / candidate
