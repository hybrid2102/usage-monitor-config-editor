"""Build a standalone Windows executable with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent


def main() -> None:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name",
        "UsageMonitorConfigEditor",
        str(ROOT / "main.py"),
    ]
    subprocess.check_call(command, cwd=ROOT)
    print(f"Build completata: {ROOT / 'dist' / 'UsageMonitorConfigEditor.exe'}")


if __name__ == "__main__":
    main()
