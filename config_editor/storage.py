"""Profile discovery, JSON validation and safe persistence."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any


class SettingsError(Exception):
    """Raised when a settings file cannot be read or validated."""


@dataclass(frozen=True)
class Profile:
    """A named settings profile managed by the editor."""

    key: str
    label: str
    directory: Path

    @property
    def path(self) -> Path:
        return self.directory / "usage-monitor-settings.json"


@dataclass
class LoadedProfile:
    """The current on-disk state of a profile."""

    profile: Profile
    data: dict[str, Any]
    exists: bool
    error: str = ""


def default_profiles(home: Path | None = None) -> list[Profile]:
    """Return the four profiles used by the current workstation setup."""
    home = home or Path.home()
    return [
        Profile("claude", "Claude", home / ".claude"),
        Profile("claude_valeria", "Claude Valeria", home / ".claude-valeria"),
        Profile("codex", "Codex", home / ".codex"),
        Profile("copilot", "Copilot", home / ".copilot"),
    ]


def load_settings(profile: Profile) -> LoadedProfile:
    """Load one profile without changing the file on disk."""
    path = profile.path
    if not path.is_file():
        return LoadedProfile(profile, {}, False)

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise SettingsError("Il file deve contenere un oggetto JSON.")
        return LoadedProfile(profile, data, True)
    except (OSError, UnicodeError, json.JSONDecodeError, SettingsError) as exc:
        return LoadedProfile(profile, {}, True, str(exc))


def save_settings(profile: Profile, data: dict[str, Any]) -> Path:
    """Write settings atomically, keeping the previous file as ``.bak``."""
    if not isinstance(data, dict):
        raise SettingsError("Le impostazioni devono essere un oggetto JSON.")

    profile.directory.mkdir(parents=True, exist_ok=True)
    path = profile.path
    backup = path.with_suffix(path.suffix + ".bak")
    if path.exists():
        shutil.copy2(path, backup)

    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}.", suffix=".tmp", dir=profile.directory
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise

    return path

