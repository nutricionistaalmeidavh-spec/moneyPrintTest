"""Contracts for the six independent scene workflow and final assembly."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts.frutalandia_scenes import (
    get_scene, scene_ids, make_scene_story, write_concat_list, expected_duration,
)
from scripts.frutalandia_kaggle_bundle import make_kernel

ROOT=Path(__file__).resolve().parents[1]
STORY=ROOT/"stories/frutalandia/contador-do-butico-ep01.json"


class ScenePipelineTests(unittest.TestCase):
    def setUp(self):
        self.story=json.loads(STORY.read_text(encoding="utf-8"))

    def test_six_scenes_of_eight_seconds(self):
        self.assertEqual(scene_ids(self.story),["s01","s02","s03","s04","s05","s06"])
        self.assertEqual(expected_duration(self.story),48)
        for sid in scene_ids(self.story):
            self.assertEqual(get_scene(self.story,sid)["seconds"],8)
            mini=make_scene_story(self.story,sid)
            self.assertEqual(mini["format"]["target_seconds"],8)
            self.assertEqual(len(mini["scenes"]),1)

    def test_correct_forehead_counters(self):
        counters={c["id"]:c["forehead_counter"] for c in self.story["characters"]}
        self.assertEqual(counters,{"moranguete":"000","uva":"007","mae-pera":"999+","pai-caju":"038"})
        self.assertEqual(self.story["scenes"][-1]["counter_override"],{"mae-pera":"ERR"})
        self.assertEqual(self.story["format"]["aspect"],"9:16")

    def test_invalid_scene_and_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            get_scene(self.story,"../../unsafe")
        damaged=json.loads(json.dumps(self.story))
        damaged["scenes"][1]["id"]="s01"
        with self.assertRaises(ValueError):
            scene_ids(damaged)

    def test_concat_requires_all_six_clips_in_order(self):
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)
            for sid in scene_ids(self.story):
                (dest/f"scene-{sid}.mp4").write_bytes(b"test")
            listing=write_concat_list(self.story,dest)
            text=listing.read_text(encoding="utf-8")
            self.assertEqual(text.count("file "),6)
            self.assertLess(text.index("scene-s01"),text.index("scene-s06"))
            (dest/"scene-s03.mp4").unlink()
            with self.assertRaises(FileNotFoundError):
                write_concat_list(self.story,dest)

    def test_kernel_targets_only_selected_scene(self):
        with tempfile.TemporaryDirectory() as folder:
            work=Path(folder)
            script=make_kernel(
                STORY, ROOT/"scripts/frutalandia_blender.py",
                ROOT/"scripts/frutalandia_episode_runner.py",
                work, "contafrutas", slug="butico-ep01-s04", scene_id="s04"
            )
            self.assertIn("'--scene-id', 's04'",script.read_text())
            metadata=json.loads((work/"kernel-metadata.json").read_text())
            self.assertEqual(metadata["id"],"contafrutas/butico-ep01-s04")
            self.assertTrue(metadata["is_private"])

if __name__=="__main__":
    unittest.main()
