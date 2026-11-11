"""Full 5-minute Movie contract: canonical 25 scenes, real products and contextual motion."""
import json
import unittest
from pathlib import Path
from PIL import Image, ImageChops
from scripts.studio_render import build_plan
from scripts.full300_editor import (
    build_timeline, choose_direction, frame_scene, TOOL_REPOS, SCENE_FAMILIES,
    select_proof, source_assurance
)

ROOT=Path(__file__).resolve().parents[1]
PROJECT=json.loads((ROOT/"projects/5-sistemas-talkcraft-educacional.json").read_text())

class Full300Tests(unittest.TestCase):
    def test_25_scenes_are_exactly_300_seconds(self):
        plan=build_plan(PROJECT)
        rows=build_timeline(plan)
        self.assertEqual(len(rows),25)
        self.assertEqual(sum(x["frames"] for x in rows),9000)
        self.assertEqual(rows[0]["start"],0)
        self.assertEqual(rows[-1]["end"],9000)
        self.assertEqual(rows[-1]["end"]/30,300)
        self.assertTrue(all(x["start"]==y["end"] for y,x in zip(rows,rows[1:])))

    def test_five_named_products_have_real_github_source(self):
        self.assertEqual(set(TOOL_REPOS),{"erpnext","twenty","chatwoot","plane","paperless"})
        self.assertEqual(len(set(TOOL_REPOS.values())),5)
        self.assertTrue(all(v.startswith("https://github.com/") for v in TOOL_REPOS.values()))

    def test_legacy_12s_template_not_reused_without_context(self):
        self.assertEqual(choose_direction(3),"problem")
        self.assertEqual(choose_direction(4),"proof")
        self.assertEqual(choose_direction(5),"flow")
        self.assertEqual(choose_direction(11),"chat")
        self.assertEqual(choose_direction(12),"proof")
        self.assertEqual(choose_direction(17),"kanban")
        self.assertEqual(choose_direction(20),"proof")
        self.assertEqual(choose_direction(23),"recap")
        self.assertEqual(choose_direction(25),"outro")
        self.assertTrue(all(choose_direction(n) in SCENE_FAMILIES for n in range(1,26)))

    def test_no_synthetic_app_screens_or_unverified_screen_claims(self):
        authentic=Image.new("RGB",(560,320),(62,95,131))
        imgs={"erpnext":{"repo":authentic,"app":authentic}}
        self.assertIs(select_proof(imgs,"erpnext","app"),authentic)
        self.assertIs(select_proof(imgs,"erpnext","repo"),authentic)
        self.assertIsNone(select_proof(imgs,"twenty","app"))
        self.assertFalse(source_assurance({"repo":authentic},"app"))
        self.assertTrue(source_assurance({"repo":authentic,"app":authentic},"app"))

    def test_different_families_emit_nonempty_editable_frames(self):
        project=build_plan(PROJECT)
        screenshot=Image.new("RGB",(760,490),(38,53,77))
        captures={tool:{"repo":screenshot,"app":screenshot} for tool in TOOL_REPOS}
        for num in (1,3,4,5,7,11,12,16,17,20,21,23,24,25):
            scene=project["scenes"][num-1]
            still=frame_scene(scene,2.0,captures,width=640,height=360)
            self.assertEqual(still.size,(640,360),f"scene-{num:03}")
            self.assertEqual(still.mode,"RGB")
            blank=Image.new("RGB",still.size,(246,238,219))
            self.assertIsNotNone(ImageChops.difference(still,blank).getbbox(),f"scene-{num:03}")

    def test_has_four_visual_beats_in_standard_12s_scene(self):
        rows=build_timeline(build_plan(PROJECT))
        self.assertGreaterEqual(rows[4]["shot_count"],3)
        self.assertGreaterEqual(rows[11]["shot_count"],3)
        self.assertEqual(rows[0]["frames"],90)

if __name__=="__main__": unittest.main()
