from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from config_editor.storage import Profile, load_settings, save_settings


class StorageTests(unittest.TestCase):
    def test_missing_profile_is_reported_without_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile = Profile("test", "Test", Path(directory) / "missing")
            loaded = load_settings(profile)
            self.assertFalse(loaded.exists)
            self.assertEqual(loaded.data, {})

    def test_save_is_json_and_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile = Profile("test", "Test", Path(directory))
            save_settings(profile, {"bar_fg": "#D97757"})
            save_settings(profile, {"bar_fg": "#E8756F"})

            self.assertEqual(json.loads(profile.path.read_text()), {"bar_fg": "#E8756F"})
            self.assertEqual(json.loads(profile.path.with_suffix(".json.bak").read_text()), {"bar_fg": "#D97757"})


if __name__ == "__main__":
    unittest.main()

