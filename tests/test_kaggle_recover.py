"""Unit tests for Kaggle media recovery: only genuine files become video artifacts."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.kaggle_recover import collect_media, recover_mp4


class RecoverTests(unittest.TestCase):
    def test_empty_folder_never_claims_video(self):
        with tempfile.TemporaryDirectory() as name:
            found=collect_media(Path(name))
            self.assertEqual(found["playable_videos"], [])
            self.assertEqual(found["files"], [])
            self.assertEqual(found["status"], "no_video_available")

    def test_invalid_mp4_not_marked_playable(self):
        with tempfile.TemporaryDirectory() as name:
            path=Path(name)
            (path/"silent.mp4").write_bytes(b"not a real mp4")
            with patch("scripts.kaggle_recover.inspect_video",return_value=None):
                found=collect_media(path)
            self.assertEqual(found["playable_videos"], [])
            self.assertEqual(found["status"],"video_unplayable")
            self.assertEqual(found["files"][0]["name"],"silent.mp4")

    def test_no_synthetic_salvage_for_broken_mp4(self):
        with tempfile.TemporaryDirectory() as name:
            source=Path(name)/"bad.mp4"
            source.write_bytes(b"broken")
            with patch("scripts.kaggle_recover.subprocess.run",side_effect=OSError("ffmpeg missing")):
                self.assertIsNone(recover_mp4(source))
            self.assertEqual(source.read_bytes(),b"broken")

    def test_csv_or_json_not_counted_as_video(self):
        with tempfile.TemporaryDirectory() as name:
            p=Path(name)
            (p/"kernel-status.txt").write_text("RUNNING")
            (p/"manifest.json").write_text('{"status": "planned"}')
            found=collect_media(p)
            self.assertEqual(found["status"],"no_video_available")
            self.assertEqual(found["playable_videos"],[])


if __name__=="__main__":
    unittest.main()
