"""Guarantee the full film uses upstream Opus motions, never Python recreations."""
import json
import unittest
from collections import Counter
from pathlib import Path
from scripts.prepare_five_systems_opus import validate_board, PROJECT, BOARD, REQUIRED_MEDIA, MOTION_SOURCES
ROOT=Path(__file__).resolve().parents[1]

class OpusOriginalFullTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project=json.loads((ROOT/PROJECT).read_text(encoding="utf-8"))
        cls.board=json.loads((ROOT/BOARD).read_text(encoding="utf-8"))

    def test_25_original_motions_cover_9000_frames(self):
        summary=validate_board(self.board,self.project)
        self.assertEqual(summary["frames"],9000)
        self.assertEqual(summary["scenes"],25)
        self.assertGreaterEqual(summary["distinct_motions"],20)
        self.assertLessEqual(summary["max_repetition"],2)

    def test_every_scene_keeps_its_canonical_narration(self):
        for src,shot in zip(self.project["scenes"],self.board["scenes"]):
            self.assertEqual(src["text"],shot["say"])
            self.assertEqual(src["duration_frames"],shot["min"])
            self.assertFalse(shot.get("layers"))
            self.assertEqual(shot["transition"]["type"],"cut")

    def test_all_proof_scenes_use_genuine_image_paths(self):
        self.assertEqual(len(REQUIRED_MEDIA),5)
        for scene_index,software in REQUIRED_MEDIA.items():
            shot=self.board["scenes"][scene_index-1]
            used=str(shot["props"])
            self.assertIn("software/"+software+"/verified.png",used)
            self.assertIn("software/"+software+"/verified.png",str(shot["props"]))
        self.assertTrue(all(url.startswith("https://github.com/") for url in MOTION_SOURCES.values()))

    def test_render_path_is_direct_original_cli_not_adapted_python(self):
        runner=(ROOT/".github/workflows/five-systems-opus-original.yml").read_text()
        self.assertIn("node cli/direct.mjs",runner)
        self.assertIn("git clone",runner)
        self.assertIn("v1.2.0",runner)
        self.assertNotIn("python -m scripts.full300_editor",runner)
        self.assertNotIn("python -m scripts.opus_motion_adapter",runner)
        self.assertIn("Piper",runner)
        self.assertIn("upload-artifact",runner)

    def test_screen_labels_do_not_expose_capture_metadata(self):
        for scene in self.board["scenes"]:
            strings=str(scene["props"]).lower()
            for forbidden in ("captura real", "screenshot do readme", "tela fictícia", "falso dashboard", "mockup fictício"):
                self.assertNotIn(forbidden,strings)

if __name__=="__main__":unittest.main()
