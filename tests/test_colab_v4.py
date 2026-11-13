"""Regression tests for Colab V4; no network, GPU, or paid provider needed."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.colab_v4 import (
    create_board, sync_frames, visual_cache_key, export_generic_shorts,
)


class ColabV4UnitTests(unittest.TestCase):
    def test_board_generates_free_canonical_project(self):
        board = create_board("Vídeo", "Primeira cena. Segunda cena!", aspect="9:16")
        self.assertEqual(board["schema_version"], 3)
        self.assertEqual(board["visual_style"], "light_motion")
        self.assertEqual(len(board["scenes"]), 2)

    def test_sync_frames_canonical_no_gaps(self):
        original = create_board("Vídeo", "Primeira cena. Segunda cena!", aspect="9:16")
        updated = sync_frames(original, [1.23, 2.01])
        self.assertEqual(updated["scenes"][0]["duration_frames"], 37)
        self.assertEqual(updated["scenes"][1]["start_frame"], 37)
        self.assertEqual(updated["scenes"][1]["duration_frames"], 61)
        self.assertEqual(updated["total_frames"], 98)
        self.assertNotEqual(updated["total_frames"], original["total_frames"])

    def test_sync_frames_rejects_invalid_timings(self):
        board = create_board("Vídeo", "Primeira cena. Segunda cena!")
        for bad in ([1.0], [1.0, float("nan")], [1.0, -1.0]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    sync_frames(board, bad)

    def test_cache_reuses_unchanged_scene_when_earlier_scene_shifts(self):
        board = create_board("Vídeo", "Primeira cena. Segunda cena!")
        scene = board["scenes"][1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "scripts" / "studio_render.py").write_text("same renderer")
            initial = visual_cache_key(scene, board, root)
            shifted = copy.deepcopy(scene)
            shifted["start_frame"] += 90
            self.assertEqual(initial, visual_cache_key(shifted, board, root))

    def test_cache_invalidated_by_renderer_change(self):
        board = create_board("Vídeo", "Primeira cena. Segunda cena!")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            renderer = root / "scripts" / "studio_render.py"
            renderer.write_text("renderer version one")
            initial = visual_cache_key(board["scenes"][0], board, root)
            renderer.write_text("renderer version two")
            self.assertNotEqual(initial, visual_cache_key(board["scenes"][0], board, root))

    def test_cache_changes_when_resolution_changes(self):
        board = create_board("Vídeo", "Cena única.")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "scripts" / "studio_render.py").write_text("renderer")
            scene = board["scenes"][0]
            preview = visual_cache_key(scene, board, root, width=320, height=180)
            fullhd = visual_cache_key(scene, board, root, width=1920, height=1080)
            self.assertNotEqual(preview, fullhd)

    def test_generic_shorts_validates_requested_count(self):
        with self.assertRaises(ValueError):
            export_generic_shorts("/missing.mp4", "/tmp/unused", [], count=0)


if __name__ == "__main__":
    unittest.main()
