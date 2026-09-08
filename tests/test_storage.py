from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from config_editor.storage import (
    Profile,
    load_profile_registry,
    load_settings,
    new_profile,
    save_profile_registry,
    save_settings,
)


class StorageTests(unittest.TestCase):
    def test_missing_profile_is_reported_without_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile = Profile("test", "Test", Path(directory) / "missing" / "usage-monitor-settings.json")
            loaded = load_settings(profile)
            self.assertFalse(loaded.exists)
            self.assertEqual(loaded.data, {})

    def test_save_is_json_and_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile = Profile("test", "Test", Path(directory) / "usage-monitor-settings.json")
            save_settings(profile, {"bar_fg": "#D97757"})
            save_settings(profile, {"bar_fg": "#E8756F"})

            self.assertEqual(json.loads(profile.path.read_text()), {"bar_fg": "#E8756F"})
            self.assertEqual(json.loads(profile.path.with_suffix(".json.bak").read_text()), {"bar_fg": "#D97757"})

    def test_profile_registry_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"LOCALAPPDATA": directory}):
                profile = new_profile("Codex", Path(directory) / "codex" / "usage-monitor-settings.json")
                save_profile_registry([profile])
                loaded = load_profile_registry()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].key, profile.key)
            self.assertEqual(loaded[0].label, "Codex")
            self.assertEqual(loaded[0].path, profile.path)


if __name__ == "__main__":
    unittest.main()
