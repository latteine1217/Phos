"""
Build Phos Desktop with PyInstaller.

What:
    產生可分發的桌面應用。

Why:
    把打包流程收斂成可重跑腳本，避免每次手打長串 PyInstaller 參數。
"""

from __future__ import annotations

import os
from pathlib import Path

import PyInstaller.__main__


ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build" / "pyinstaller"
DIST_DIR = ROOT / "dist"
DATA_DIR = ROOT / "data"


def main() -> None:
    """
    What:
        執行 PyInstaller 打包。

    Why:
        將桌面入口與必要資料檔一起封裝，避免 app 啟動後找不到物理資料表。
    """
    add_data_arg = f"{DATA_DIR}{os.pathsep}data"
    PyInstaller.__main__.run(
        [
            str(ROOT / "phos_desktop_app.py"),
            "--name=Phos",
            "--noconfirm",
            "--windowed",
            f"--distpath={DIST_DIR}",
            f"--workpath={BUILD_DIR}",
            f"--specpath={BUILD_DIR}",
            f"--add-data={add_data_arg}",
        ]
    )


if __name__ == "__main__":
    main()
