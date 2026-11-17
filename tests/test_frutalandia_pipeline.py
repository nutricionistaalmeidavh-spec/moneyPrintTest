"""Regression tests for private Kaggle bundling and final media contracts."""
import base64
import json
import tempfile
import unittest
from pathlib import Path
from scripts.frutalandia_kaggle_bundle import make_kernel

ROOT=Path(__file__).resolve().parents[1]
EP=ROOT/"stories/frutalandia/audio-do-amanha-ep01.json"


class FrutalandiaBundleTests(unittest.TestCase):
    def test_script_contains_no_credentials_and_bundles_original_episode(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            build=make_kernel(EP,ROOT/"scripts/frutalandia_blender.py",
                              ROOT/"scripts/frutalandia_episode_runner.py",
                              target,"fruitcreator")
            text=build.read_text(encoding="utf-8")
            self.assertIn("render_episode.py",text)
            self.assertNotIn("KAGGLE_API_TOKEN",text)
            self.assertNotIn("GITHUB_TOKEN",text)
            meta=json.loads((target/"kernel-metadata.json").read_text())
            self.assertTrue(meta["is_private"])
            self.assertTrue(meta["enable_gpu"])
            self.assertTrue(meta["enable_internet"])
            self.assertEqual(meta["machine_shape"],"NvidiaTeslaT4")
            self.assertEqual(meta["id"],"fruitcreator/frutalandia-ep01")
            self.assertIn("Frutalandia",meta["title"])

    def test_rejects_unsafe_slugs(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                make_kernel(EP,ROOT/"scripts/frutalandia_blender.py",
                            ROOT/"scripts/frutalandia_episode_runner.py",
                            Path(tmp),"../private")

    def test_story_unchanged_by_bundle(self):
        raw=EP.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            make_kernel(EP,ROOT/"scripts/frutalandia_blender.py",
                        ROOT/"scripts/frutalandia_episode_runner.py",
                        Path(tmp),"fruitcreator")
        self.assertEqual(EP.read_bytes(),raw)

    def test_renderer_has_real_blender_and_audio_generation(self):
        source=(ROOT/"scripts/frutalandia_episode_runner.py").read_text()
        blender=(ROOT/"scripts/frutalandia_blender.py").read_text()
        self.assertIn("bpy.ops.render.render(animation=True)",blender)
        self.assertIn("voices_piper",source)
        self.assertIn("ffprobe",source)
        self.assertIn("frutalandia-ep01.mp4",source)
        self.assertIn("VoiceStudio",source)
        self.assertNotIn("fake_video",source)


if __name__ == "__main__":
    unittest.main()
