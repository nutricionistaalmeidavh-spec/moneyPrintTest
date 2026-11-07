"""Contract for real I2V, consistent reference and zero-paid execution.

No GPU is necessary to run these tests.
"""
import base64
import json
import tempfile
import unittest
from pathlib import Path

from scripts.frutalandia_i2v import (
    load_story, get_scene_prompt, read_reference, prepare_reference,
    validate_preview, check_available_gpu, REFERENCE_B64,
)

ROOT=Path(__file__).resolve().parents[1]


class ReferenceI2VTests(unittest.TestCase):
    def test_original_generated_reference_is_committed_not_remote_url(self):
        self.assertTrue(REFERENCE_B64.is_file())
        data=base64.b64decode(REFERENCE_B64.read_text().strip(),validate=True)
        self.assertTrue(data.startswith(b"RIFF"))
        self.assertEqual(data[8:12],b"WEBP")
        manifest=json.loads((ROOT/"assets/frutalandia/reference-manifest.json").read_text())
        import hashlib
        self.assertEqual(hashlib.sha256(data).hexdigest(),manifest["sha256"])
        self.assertIn("source_original_sha256",manifest)
        self.assertEqual(manifest["canonical_counters"],
                         {"moranguete":"000","uva":"007","mae-pera":"999+","pai-caju":"038"})

    def test_prompts_use_story_and_not_numbers_in_picture(self):
        story=load_story(ROOT/"stories/frutalandia/contador-do-butico-ep01.json")
        self.assertEqual(len(story["scenes"]),6)
        for scene in story["scenes"]:
            prompt=get_scene_prompt(story,scene["id"])
            self.assertIn(scene["action"],prompt)
            self.assertIn("Nordeste",prompt)
            self.assertIn("same character",prompt)
        self.assertIn("999+",get_scene_prompt(story,"s06"))
        with self.assertRaises(ValueError):
            get_scene_prompt(story,"s00")

    def test_reference_pack_produces_six_portrait_first_frames(self):
        story=load_story(ROOT/"stories/frutalandia/contador-do-butico-ep01.json")
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            files=prepare_reference(story,out)
            self.assertEqual(len(files),6)
            from PIL import Image
            for path in files:
                with Image.open(path) as im:
                    self.assertEqual(im.size,(320,576))
            self.assertTrue((out/"reference-report.json").exists())

    def test_gpu_fail_fast(self):
        class NoneTorch:
            class cuda:
                @staticmethod
                def is_available(): return False
        with self.assertRaisesRegex(RuntimeError,"GPU NVIDIA"):
            check_available_gpu(NoneTorch)

    def test_no_placeholder_mp4_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"preview.mp4"
            file.write_bytes(b"FAKE_MP4")
            with self.assertRaises(Exception):
                validate_preview(file,expected_seconds=2.0)

    def test_actions_only_prepares_on_hosted_runner(self):
        text=(ROOT/".github/workflows/frutalandia-i2v.yml").read_text()
        self.assertIn("actions/upload-artifact@v4",text)
        self.assertIn("self-hosted",text)
        self.assertIn("frutalandia-gpu",text)
        self.assertIn("workflow_dispatch:",text)
        self.assertNotIn("KAGGLE_API_TOKEN",text)
        self.assertNotIn("OPENAI_API_KEY",text)


if __name__=="__main__":
    unittest.main()
