"""Regression coverage for frame-exact MoneyPrint Studio V3 rendering."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.studio_render import RenderError, build_plan, render_project, word_cues


def sample():
    return {
        "schema_version": 3, "id": "test-project", "revision": 1,
        "topic": "Exemplo MoneyPrint", "script": "Exemplo de roteiro", "fps": 30,
        "aspect": "16:9", "total_frames": 90,
        "tracks": [{"id": "video", "kind": "video"}], "assets": [],
        "scenes": [
            {"id": "scene-001", "track_id": "video", "title": "Comece com o problema",
             "text": "Você precisa organizar os clientes.", "kind": "text", "asset_id": None,
             "start_frame": 0, "duration_frames": 30, "animation": "cut", "framing": "contain", "layout": "hero"},
            {"id": "scene-002", "track_id": "video", "title": "A ferramenta",
             "text": "Conheça uma solução de CRM.", "kind": "text", "asset_id": None,
             "start_frame": 30, "duration_frames": 60, "animation": "slide", "framing": "contain", "layout": "flow"},
        ],
    }


class PlanTests(unittest.TestCase):
    def test_canonical_frames_are_preserved(self):
        plan = build_plan(sample())
        self.assertEqual(plan["total_frames"], 90)
        self.assertEqual([s["start_frame"] for s in plan["scenes"]], [0, 30])
        self.assertEqual([s["end_frame"] for s in plan["scenes"]], [30, 90])

    def test_rejects_gap_and_overlapping_scenes(self):
        p = sample()
        p["scenes"][1]["start_frame"] = 29
        with self.assertRaises(RenderError): build_plan(p)
        p["scenes"][1]["start_frame"] = 31
        with self.assertRaises(RenderError): build_plan(p)

    def test_media_must_have_verified_license_and_safe_local_path(self):
        p = sample()
        p["assets"] = [{"id": "image", "path": "assets/../secrets.txt",
                         "verified": True, "license": "CC0", "attribution": "author"}]
        p["scenes"][0]["asset_id"] = "image"
        with self.assertRaises(RenderError): build_plan(p)
        p["assets"][0]["path"] = "assets/approved/still.png"
        p["assets"][0]["license"] = ""
        with self.assertRaises(RenderError): build_plan(p)

    def test_word_cues_are_labelled_estimates_not_forced_alignment(self):
        cues = word_cues("um novo sistema", 3.0, 4.0)
        self.assertEqual(len(cues), 3)
        self.assertEqual(cues[0]["method"], "estimated")
        self.assertAlmostEqual(cues[0]["start"], 3.0)
        self.assertAlmostEqual(cues[-1]["end"], 7.0)

    def test_rejects_invalid_storyboard_visual_data(self):
        p = sample()
        p["scenes"][1]["flow_steps"] = ["Lead", "Em negociação", "Concluído"]
        p["scenes"][1]["bullets"] = ["Contato", "Proposta", "Fechamento"]
        plan = build_plan(p)
        self.assertEqual(plan["scenes"][1]["flow_steps"][1], "Em negociação")
        p["scenes"][1]["flow_steps"] = ["ok", "ok", "<script>alert(1)</script>"]
        with self.assertRaises(RenderError): build_plan(p)

    def test_flow_progression_produces_distinct_stages(self):
        from scripts.studio_render import _slide
        from PIL import Image, ImageChops
        with tempfile.TemporaryDirectory() as d:
            p = sample()["scenes"][1]
            p["flow_steps"] = ["Contato", "Proposta", "Venda"]
            a, b = Path(d)/"stage-a.png", Path(d)/"stage-b.png"
            _slide(p,a,640,360,None,stage=0)
            _slide(p,b,640,360,None,stage=2)
            with Image.open(a) as left, Image.open(b) as right:
                self.assertIsNotNone(ImageChops.difference(left,right).getbbox())

    @unittest.skipUnless(__import__("shutil").which("ffmpeg") and __import__("shutil").which("ffprobe"), "ffmpeg required")
    def test_video_with_dynamic_beats_remains_exact_frames(self):
        with tempfile.TemporaryDirectory() as d:
            p=sample()
            p["scenes"][1]["flow_steps"]=["Lead", "Proposta", "Cliente"]
            result=render_project(p,Path(d),Path(d)/"out",voice="none",width=320,height=180)
            self.assertEqual(result["total_frames"],90)
            self.assertEqual(result["scenes_rendered"],2)
            self.assertGreaterEqual(result["visual_beats"],5)

    def test_plan_can_import_without_pillow_in_validation_only(self):
        # GitHub Actions validates JSON before installing the rendering stack.
        import sys
        env = dict(__import__('os').environ)
        env['PYTHONPATH'] = str(Path(__file__).resolve().parents[1])
        result = subprocess.run([sys.executable, '-S', '-c',
            'from scripts.studio_render import build_plan; print(build_plan({"schema_version": 3, "fps": 30, "aspect": "16:9", "assets": [], "scenes": [], "total_frames": 0}))'],
            text=True, capture_output=True, env=env)
        # It may fail due to invalid project content, but never due to absent Pillow.
        self.assertNotIn('ModuleNotFoundError', result.stderr)

    def test_missing_or_offline_media_is_rejected_not_fake_screenshot(self):
        with tempfile.TemporaryDirectory() as d:
            p = sample()
            p["assets"] = [{"id": "image", "path": "assets/does-not-exist.png",
                             "verified": True, "license": "CC0", "attribution": "author"}]
            p["scenes"][0]["asset_id"] = "image"
            with self.assertRaises(RenderError): render_project(p, Path(d), Path(d)/"out", voice="none", width=320, height=180)

    @unittest.skipUnless(__import__("shutil").which("ffmpeg") and __import__("shutil").which("ffprobe"), "ffmpeg required")
    def test_real_mp4_exact_frames_and_timing(self):
        with tempfile.TemporaryDirectory() as d:
            result = render_project(sample(), Path(d), Path(d)/"out", voice="none", width=320, height=180)
            data = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-count_frames", "-show_entries", "stream=nb_read_frames",
                "-of", "json", result["output"]], text=True))
            self.assertEqual(int(data["streams"][0]["nb_read_frames"]), 90)
            self.assertEqual(result["total_frames"], 90)
            self.assertTrue(Path(result["credits"]).is_file())
            self.assertEqual(result["word_alignment"], "estimated")


if __name__ == "__main__":
    unittest.main()