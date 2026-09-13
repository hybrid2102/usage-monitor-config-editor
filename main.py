import os
from pathlib import Path
import sys


# PyInstaller normally configures this path through its Qt hook. Keeping an
# explicit handle here also prevents another Qt installation on PATH from
# being selected before the DLLs bundled with the executable.
_qt_dll_directories = []
if getattr(sys, "frozen", False):
    _bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    _qt_directories = (_bundle_root / "PySide6", _bundle_root)
    os.environ["PATH"] = os.pathsep.join(
        [*(str(directory) for directory in _qt_directories), os.environ.get("PATH", "")]
    )
    for _qt_directory in _qt_directories:
        if _qt_directory.is_dir() and hasattr(os, "add_dll_directory"):
            _qt_dll_directories.append(os.add_dll_directory(str(_qt_directory)))


from config_editor.main_window import run


if __name__ == "__main__":
    raise SystemExit(run())
