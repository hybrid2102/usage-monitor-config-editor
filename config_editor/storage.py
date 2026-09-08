"""Profile discovery, JSON validation and safe persistence."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any
import uuid


class SettingsError(Exception):
    """Raised when a settings file cannot be read or validated."""


@dataclass(frozen=True)
class Profile:
    """A named settings profile managed by the editor."""

    key: str
    label: str
    path: Path

    @property
    def directory(self) -> Path:
        return self.path.parent


@dataclass
class LoadedProfile:
    """The current on-disk state of a profile."""

    profile: Profile
    data: dict[str, Any]
    exists: bool
    error: str = ""


def default_profiles(home: Path | None = None) -> list[Profile]:
    """Return the former built-in profiles for callers that still need them."""
    home = home or Path.home()
    return [
        Profile("claude", "Claude", home / ".claude" / "usage-monitor-settings.json"),
        Profile("claude_valeria", "Claude Valeria", home / ".claude-valeria" / "usage-monitor-settings.json"),
        Profile("codex", "Codex", home / ".codex" / "usage-monitor-settings.json"),
        Profile("copilot", "Copilot", home / ".copilot" / "usage-monitor-settings.json"),
    ]


def profile_registry_path() -> Path:
    """Return the per-user registry used to remember selected profiles."""
    local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return local_app_data / "UsageMonitorConfigEditor" / "profiles.json"


def load_profile_registry() -> list[Profile]:
    """Load remembered profiles, returning an empty list on first run."""
    path = profile_registry_path()
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        entries = payload.get("profiles", []) if isinstance(payload, dict) else []
        if not isinstance(entries, list):
            return []
        profiles: list[Profile] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            key = entry.get("key")
            label = entry.get("label")
            raw_path = entry.get("path")
            if isinstance(key, str) and isinstance(label, str) and isinstance(raw_path, str) and raw_path.strip():
                profiles.append(Profile(key, label or Path(raw_path).stem, Path(raw_path)))
        return profiles
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []


def save_profile_registry(profiles: list[Profile]) -> Path:
    """Persist the selected profile list atomically."""
    path = profile_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = path.with_suffix(path.suffix + ".bak")
    if path.exists():
        shutil.copy2(path, backup)
    payload = {
        "version": 1,
        "profiles": [
            {"key": profile.key, "label": profile.label, "path": str(profile.path)}
            for profile in profiles
        ],
    }
    fd, temporary_name = tempfile.mkstemp(prefix=".profiles.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
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


def new_profile(label: str, path: Path) -> Profile:
    """Create a profile with a stable key for the local registry."""
    return Profile(f"profile_{uuid.uuid4().hex}", label, path)


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
