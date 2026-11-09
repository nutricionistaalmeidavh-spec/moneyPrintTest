import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.motion_pipeline import (
    validate_motion_options, render_motion_first, plan_capture, resolve_asset, 
    scene_boundaries, quality_report, build_adapter_command,
)


class MotionPipelineTests(unittest.TestCase):
    def test_motion_defaults_are_free_and_preserve_hard_cuts(self):
        config=validate_motion_options({})
        self.assertEqual(config["transition"],"cut")
        self.assertEqual(config["universe"],True)
        self.assertFalse(config["silence_cut"])
        self.assertEqual(config["renderer"],"ffmpeg")

    def test_rejects_unsafe_user_media_and_unexpected_options(self):
        with self.assertRaises(ValueError):
            validate_motion_options({"hook_path":"../secret.mp4"})
        with self.assertRaises(ValueError):
            validate_motion_options({"hook_path":"https://example.com/a.mp4"})
        with self.assertRaises(ValueError):
            validate_motion_options({"external_api_key":"bad"})
        with self.assertRaises(ValueError):
            validate_motion_options({"hook_seconds":11})
        with self.assertRaises(ValueError):
            resolve_asset("assets/../../passwd", Path.cwd())

    def test_capture_plan_contains_smooth_camera_motion(self):
        plan=plan_capture(30, 3)
        self.assertEqual(len(plan),3)
        self.assertEqual(plan[0]["camera"],"ease_in_out")
        self.assertEqual(sum(i["seconds"] for i in plan),30)

    def test_scene_indexer_uses_explicit_times_not_fabricated_cuts(self):
        self.assertEqual(scene_boundaries([(0, 1.2), (1.2, 5)]),[{"start":0.0,"end":1.2},{"start":1.2,"end":5.0}])
        with self.assertRaises(ValueError):
            scene_boundaries([(2,1)])

    def test_local_adapter_commands_avoid_shells_and_external_apis(self):
        self.assertEqual(build_adapter_command("openscreen_export","demo.openscreen","out.mp4")[:2],["openscreen","export"])
        self.assertEqual(build_adapter_command("hyperframes_render","project","out.mp4")[:3],["npx","--no-install","hyperframes"])
        with self.assertRaises(ValueError):
            build_adapter_command("unknown","x","y")

    def test_render_routes_to_existing_cinematic_renderer(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch("scripts.cinematic_render.render_cinematic",return_value={"status":"success","output":str(root/"video_1.mp4")}) as existing:
                (root/"video_1.mp4").write_bytes(b"fixture")
                data={"topic":"video", "motion":validate_motion_options({"universe":False})}
                result=render_motion_first(data,root,root,{},verify_media=False)
                self.assertEqual(result["status"],"success")
                existing.assert_called_once()
                self.assertEqual(result["motion_pipeline"],"p0-p2")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"requires FFmpeg")
    def test_quality_report_checks_real_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"sample.mp4"
            subprocess.run(["ffmpeg","-loglevel","error","-y","-f","lavfi","-i","testsrc2=s=160x90:r=15:d=1","-c:v","mpeg4",str(target)],check=True)
            result=quality_report(target)
            self.assertEqual(result["video_streams"],1)
            self.assertGreater(result["duration_seconds"],0.9)
            self.assertEqual(result["width"],160)
            self.assertEqual(result["height"],90)


if __name__ == "__main__":
    unittest.main()
