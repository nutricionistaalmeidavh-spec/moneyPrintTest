"""Regression tests for the opt-in zero-cost video stack."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.video_stack import (
    VideoStackError, normalize_motion_options, plan_intro, safe_asset,
    index_scenes, ffprobe_media,
)


class VideoStackTests(unittest.TestCase):
    def test_intro_is_hard_cut_and_not_slowed(self):
        self.assertEqual(plan_intro(2.4, 0, 40), [("hook", 2.4), ("body", 40)])
        self.assertEqual(plan_intro(1.6, 2.2, 10), [
            ("hook", 1.6), ("universe", 2.2), ("body", 10),
        ])

    def test_rejects_invalid_options(self):
        for raw in ({"hook_seconds": -1}, {"universe_seconds": 99},
                    {"transition": "white_flash"}, {"hook_asset": "../etc/passwd"},
                    {"hook_asset": "https://example.com/clip.mp4"}):
            with self.subTest(raw=raw), self.assertRaises(VideoStackError):
                normalize_motion_options(raw)

    def test_no_external_assets_or_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "hook.mp4").write_bytes(b"placeholder")
            self.assertEqual(safe_asset("assets/hook.mp4", root / "assets"),
                             (root / "assets" / "hook.mp4").resolve())
            for value in ("assets/../secret.mp4", "/tmp/clip.mp4",
                          "https://example.com/clip.mp4", "assets/ok.txt"):
                with self.subTest(value=value), self.assertRaises(VideoStackError):
                    safe_asset(value, root / "assets")

    def test_scene_index_is_deterministic_and_offline(self):
        fake_scene = [(type("T", (), {"get_seconds": lambda self: 0.0})(),
                       type("T", (), {"get_seconds": lambda self: 2.5})())]
        with patch("scripts.video_stack.scene_detect_api", return_value=fake_scene):
            result = index_scenes("dummy.mp4")
        self.assertEqual(result[0]["start"], 0.0)
        self.assertEqual(result[0]["end"], 2.5)

    def test_ffprobe_reports_video_and_audio(self):
        with patch("scripts.video_stack.subprocess.run") as run:
            run.return_value.stdout = '{"format":{"duration":"4.25"},"streams":[{"codec_type":"video","width":320,"height":180},{"codec_type":"audio"}]}'
            result = ffprobe_media("clip.mp4")
        self.assertEqual(result["duration"], 4.25)
        self.assertTrue(result["has_audio"])


class PipelineTests(unittest.TestCase):
    def test_cinematic_import_and_default_route(self):
        from scripts.motion_pipeline import render_motion_first
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            original = {"status": "success", "output": str(dest / "video_1.mp4")}
            with patch("scripts.cinematic_render.render_cinematic", return_value=original):
                result = render_motion_first(
                    {"topic": "Tutorial", "motion": {}}, dest, dest / "runtime", {})
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["output"], original["output"])

    def test_motion_overlays_never_activate_implicitly(self):
        options = normalize_motion_options({})
        self.assertFalse(options["auto_cut"])
        self.assertEqual(options["universe_seconds"], 0)
        self.assertIsNone(options["hook_asset"])


if __name__ == "__main__":
    unittest.main()
