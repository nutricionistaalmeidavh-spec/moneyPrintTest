"""Preproduction QA: director storyboard matches canonical MoneyPrint video.

No automatic video render or paid dependency in this test.
"""
import json
import unittest
from pathlib import Path

from scripts.validate_director_storyboard import validate_board

ROOT=Path(__file__).resolve().parents[1]
BOARD=ROOT/"storyboards/5-sistemas-director-v1.json"
PROJECT=ROOT/"projects/5-sistemas-talkcraft-educacional.json"

class DirectorBoardTests(unittest.TestCase):
    def setUp(self):
        self.board=json.loads(BOARD.read_text(encoding="utf-8"))
        self.project=json.loads(PROJECT.read_text(encoding="utf-8"))

    def test_frame_exact_contiguous_original_25_scene_timeline(self):
        report=validate_board(self.board,self.project)
        self.assertEqual(report["total_frames"],9000)
        self.assertEqual(report["scene_count"],25)
        self.assertEqual(report["seconds"],300)
        self.assertTrue(report["approved_to_render"] is False)

    def test_no_reused_full_screen_or_backwards_transition(self):
        self.assertEqual(len({s["visual"]["composition_id"] for s in self.board["shots"]}),25)
        self.assertEqual([s["scene_id"] for s in self.board["shots"]],
                         [s["id"] for s in self.project["scenes"]])
        for i,s in enumerate(self.board["shots"]):
            self.assertEqual(s["timeline"]["start_frame"],
                             self.project["scenes"][i]["start_frame"])
            self.assertEqual(s["timeline"]["duration_frames"],
                             self.project["scenes"][i]["duration_frames"])
            self.assertEqual(s["transition"]["to_scene"],
                             self.board["shots"][i+1]["scene_id"] if i<24 else None)
            self.assertNotEqual(s["transition"]["type"],"return_to_previous")

    def test_beats_include_visual_brief_and_explicit_animation_instructions(self):
        for shot in self.board["shots"]:
            self.assertGreaterEqual(len(shot["motion_beats"]),3)
            self.assertGreaterEqual(len(shot["visual"]["layers"]),3)
            self.assertTrue(shot["visual"]["intent"])
            self.assertTrue(shot["visual"]["composition"])
            self.assertTrue(shot["visual"]["primary_metaphor"])
            self.assertTrue(shot["visual"]["palette"])
            for cue in shot["motion_beats"]:
                self.assertGreaterEqual(cue["at_s"],0)
                self.assertLess(cue["at_s"],shot["timeline"]["duration_frames"]/30)
                self.assertTrue(cue["action"])
                self.assertIn(cue["timing"],["editorial","word_anchor_pending"])

    def test_sources_and_pending_assets_are_explicit(self):
        report=validate_board(self.board,self.project)
        self.assertGreater(report["pending_assets"],0)
        self.assertTrue(all(x["kind"] in {"original_vector","generated_cutout",
                          "github_capture","own_broll","typography"}
                        for x in self.board["assets"]))
        self.assertTrue(all(x["license"] for x in self.board["assets"]))
        self.assertNotIn("auto_publish",self.board.get("render",{}))

    def test_detects_slide_repetition_drift(self):
        invalid=json.loads(json.dumps(self.board))
        invalid["shots"][8]["visual"]["composition_id"]=invalid["shots"][7]["visual"]["composition_id"]
        with self.assertRaisesRegex(ValueError,"composition"):
            validate_board(invalid,self.project)

    def test_detects_shifted_frame(self):
        invalid=json.loads(json.dumps(self.board))
        invalid["shots"][15]["timeline"]["start_frame"]+=10
        with self.assertRaisesRegex(ValueError,"frame"):
            validate_board(invalid,self.project)

    def test_narration_is_canonical_and_keyword_cues_not_fabricated(self):
        for i,s in enumerate(self.board["shots"]):
            self.assertEqual(s["narration"],self.project["scenes"][i]["text"])
            self.assertEqual(s["audio_sync"]["mode"],"word_anchor_to_align")
            self.assertEqual(s["audio_sync"]["timestamps_confirmed"],False)
        self.assertEqual(self.board["production_status"],"awaiting_visual_approval")

if __name__=="__main__": unittest.main()
