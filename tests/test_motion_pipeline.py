"""P0–P2 contract tests (no external account or paid API)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.video_stack import (
    VideoStackError, normalize_motion_options, safe_asset, plan_intro, 
    index_scenes, render_adapter, ffprobe_media,
)
from scripts.motion_pipeline import render_motion_first


class MotionPipelineContracts(unittest.TestCase):
    def test_free_defaults_keep_old_modes_unchanged(self):
        conf=normalize_motion_options({})
        self.assertEqual(conf["transition"], "cut")
        self.assertEqual(conf["universe_seconds"],0)
        self.assertFalse(conf["auto_cut"])
        self.assertIsNone(conf["hook_asset"])

    def test_media_paths_do_not_escape_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/"assets"
            self.assertEqual(safe_asset("assets/demo.mp4",root),(root/"demo.mp4").resolve())
            for bad in ("../secret.mp4","assets/../../secret.mp4","https://evil/clip.mp4","assets/info.txt"):
                with self.subTest(bad=bad),self.assertRaises(VideoStackError):
                    safe_asset(bad,root)

    def test_invalid_options_are_rejected(self):
        for invalid in ({"hook_seconds":11},{"transition":"white_flash"},{"threejs":"true"},{"api_token":"x"}):
            with self.subTest(invalid=invalid),self.assertRaises(VideoStackError):
                normalize_motion_options(invalid)

    def test_short_hook_precedes_motion_and_narrated_body(self):
        self.assertEqual(plan_intro(1.8,1.2,15),[
            ("hook",1.8),("universe",1.2),("body",15)
        ])

    def test_scene_index_keeps_verified_timestamps(self):
        class Time:
            def __init__(self,t):self.t=t
            def get_seconds(self):return self.t
        with patch("scripts.video_stack.scene_detect_api",return_value=[(Time(0),Time(1.2)),(Time(1.2),Time(5))]):
            self.assertEqual(index_scenes("dummy.mp4"),[
                {"start":0.0,"end":1.2},{"start":1.2,"end":5.0}
            ])

    def test_default_motion_routes_to_existing_cinematic_renderer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            original={"status":"success","output":str(root/"video_1.mp4")}
            with patch("scripts.motion_pipeline._render_motion_base",return_value=original) as base:
                result=render_motion_first({"topic":"Video","motion":{}},root,root,{})
                self.assertEqual(result,original)
                base.assert_called_once()

    def test_srt_shift_preserves_narration_alignment_after_intro(self):
        from scripts.motion_pipeline import shift_srt_cues
        source = "1\n00:00:00,000 --> 00:00:01,250\nOPEN SOURCE\n\n"
        expected = "1\n00:00:02,400 --> 00:00:03,650\nOPEN SOURCE\n\n"
        self.assertEqual(shift_srt_cues(source, 2.4), expected)
        with self.assertRaises(ValueError):
            shift_srt_cues(source, -1)

    def test_openscreen_cli_is_opt_in_and_no_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"out.mp4"
            def create(argv, **kwargs):
                self.assertEqual(argv[:2],["openscreen","export"])
                self.assertNotIn("shell",kwargs)
                output.write_bytes(b"dummy")
            with patch("scripts.video_stack.shutil.which",return_value="/usr/bin/openscreen"),patch("scripts.video_stack.checked_run",side_effect=create),patch("scripts.video_stack.ffprobe_media",return_value={"duration":1}):
                self.assertEqual(render_adapter("openscreen",Path("demo.openscreen"),output),output)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg required")
    def test_ffprobe_reads_real_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"short.mp4"
            subprocess.run(["ffmpeg","-loglevel","error","-y","-f","lavfi","-i",
                "testsrc2=s=160x90:r=15:d=1","-c:v","mpeg4",str(path)],check=True)
            media=ffprobe_media(path)
            self.assertEqual(media["width"],160)
            self.assertFalse(media["has_audio"])
            self.assertGreater(media["duration"],.9)


if __name__=="__main__":
    unittest.main()
