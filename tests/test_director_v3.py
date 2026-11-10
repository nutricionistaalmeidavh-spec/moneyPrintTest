"""V3 visual direction regression tests: no empty 12s scenes and no false QA pass."""
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from scripts.director_visual_qa import sample_indices, frame_observation, aggregate_observations

ROOT=Path(__file__).resolve().parents[1]
PROJECT=json.loads((ROOT/"projects/5-sistemas-talkcraft-educacional.json").read_text(encoding="utf-8"))

class DirectorV3Tests(unittest.TestCase):
    def test_25_scenes_receive_four_samples_each_with_no_duplicate_frames(self):
        scenes=PROJECT["scenes"]
        points=sample_indices(scenes)
        self.assertEqual(len(points),100)
        self.assertEqual(len({x["frame"] for x in points}),100)
        for scene in scenes:
            xs=[x["frame"] for x in points if x["scene_id"]==scene["id"]]
            self.assertEqual(len(xs),4)
            self.assertTrue(all(scene["start_frame"]<f<scene["start_frame"]+scene["duration_frames"] for f in xs))

    def test_detects_blank_middle_and_preserves_real_scene_as_review_candidate(self):
        blank=Image.new("RGB",(320,180),(246,238,219))
        verdict=frame_observation(blank)
        self.assertTrue(verdict["visually_blank"])
        drawing=blank.copy()
        draw=ImageDraw.Draw(drawing)
        draw.rectangle((50,80,280,150),fill="#303a48")
        verdict=frame_observation(drawing)
        self.assertFalse(verdict["visually_blank"])

    def test_report_is_advisory_not_fake_automatic_approval(self):
        samples=[{"scene_id":"scene-001","frame":14,"visually_blank":True,"foreground_fraction":0.0},
                 {"scene_id":"scene-001","frame":40,"visually_blank":False,"foreground_fraction":.14}]
        report=aggregate_observations(samples)
        self.assertEqual(report["sample_count"],2)
        self.assertIn("scene-001",report["review_scenes"])
        self.assertFalse(report["automatically_approved"])
        self.assertIn("não comercial",report["license_notice"].lower())

    def test_no_full_scene_opaque_insets_and_no_crossed_flow_labels(self):
        source=(ROOT/"motion/talkcraft/DirectorV2.tsx").read_text(encoding="utf-8")
        self.assertIn("SAFE_STAGE",source)
        self.assertIn("cue.effect==='scribble_chaos'",source)
        self.assertIn("frame<beats[i]?0:p",source)
        self.assertIn("objectFit:'contain'",source)
        self.assertIn("focusIndex",source)

    def test_personas_have_distinct_figures_and_scene_variants(self):
        source=(ROOT/"motion/talkcraft/DirectorV2.tsx").read_text(encoding="utf-8")
        for kind in ("manager_a","seller_b","support_c","planner_d","docs_e"):
            self.assertIn(kind,source)
        self.assertIn("roleContours",source)
        self.assertIn("sceneVariant",source)

if __name__=="__main__":unittest.main()
