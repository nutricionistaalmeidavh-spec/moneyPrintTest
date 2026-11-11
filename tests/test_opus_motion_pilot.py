"""Proofs for the adapted Opus Motion Library animations (MIT, no Remotion runtime)."""
import unittest
from pathlib import Path
from PIL import ImageChops
from scripts.opus_motion_adapter import MOTION_SEGMENTS, get_motion_name, motion_frame

ROOT=Path(__file__).resolve().parents[1]

class OpusMotionPilotTests(unittest.TestCase):
    def test_vendor_contains_original_mit_sources_used(self):
        selected={
          "breaking-news-takeover":"hud/breaking-news-takeover.tsx",
          "cause-effect-chain":"data/cause-effect-chain.tsx",
          "board-camera":"camera/board-camera.tsx",
        }
        self.assertEqual([m["id"] for m in MOTION_SEGMENTS],list(selected))
        for id,path in selected.items():
            source=ROOT/"vendor/opus-motion/src/motions"/path
            self.assertTrue(source.is_file(),str(source))
            self.assertIn(id,source.read_text(encoding="utf-8"))
        self.assertIn("MIT License",(ROOT/"vendor/opus-motion/LICENSE").read_text(encoding="utf-8"))

    def test_motions_cover_first_12s_and_not_app_demo(self):
        self.assertEqual([round(x["start"],2) for x in MOTION_SEGMENTS],[0,3.3,9.05])
        self.assertEqual([round(x["end"],2) for x in MOTION_SEGMENTS],[3.3,9.05,12])
        self.assertEqual(get_motion_name(1),"breaking-news-takeover")
        self.assertEqual(get_motion_name(7),"cause-effect-chain")
        self.assertEqual(get_motion_name(10),"board-camera")
        self.assertIsNone(get_motion_name(12.1))

    def test_animated_frames_change_and_are_not_blank(self):
        for t in (0.7,4.9,10.7):
            first=motion_frame(t,width=640,height=360)
            second=motion_frame(t+0.35,width=640,height=360)
            self.assertEqual(first.size,(640,360))
            self.assertEqual(first.mode,"RGB")
            self.assertIsNotNone(ImageChops.difference(first,second).getbbox(),str(t))

    def test_no_fake_news_or_fake_budget_numbers(self):
        for segment in MOTION_SEGMENTS:
            self.assertNotIn("live",str(segment).lower())
            self.assertNotIn("news",str(segment.get("text","")).lower())
            self.assertNotIn("r$",str(segment).lower())

if __name__=="__main__":unittest.main()
