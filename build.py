"""Build a standalone Windows executable with Nuitka and PySide6 support."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent
BUILD_OUTPUT = ROOT / "build" / "nuitka"
OUTPUT_NAME = "UsageMonitorConfigEditor.exe"


def main() -> None:
    try:
        from PySide6 import QtCore  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "PySide6 non è disponibile nell'ambiente di build. "
            "Attiva .venv e installa requirements.txt prima di riprovare."
        ) from exc

    command = [
        sys.executable,
        "-m",
        "nuitka",
        str(ROOT / "main.py"),
        "--follow-imports",
        "--enable-plugin=pyside6",
        f"--output-dir={BUILD_OUTPUT}",
        f"--output-filename={OUTPUT_NAME}",
        "--quiet",
        "--noinclude-qt-translations",
        "--onefile",
        "--noinclude-dlls=*.cpp.o",
        "--noinclude-dlls=*.qsb",
        "--windows-console-mode=disable",
        "--include-qt-plugins=generic,iconengines,imageformats,platforminputcontexts,platforms,styles",
        "--assume-yes-for-downloads",
    ]
    subprocess.check_call(command, cwd=ROOT)

    produced = BUILD_OUTPUT / OUTPUT_NAME
    target = ROOT / "dist" / OUTPUT_NAME
    if not produced.is_file():
        raise RuntimeError(f"Nuitka non ha prodotto l'eseguibile atteso: {produced}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(produced, target)
    print(f"Build completata: {target}")


if __name__ == "__main__":
    main()
