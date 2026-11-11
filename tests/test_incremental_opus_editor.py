"""Regression: re-render only broken upstream Opus scenes, splice clean clips, cut A/V silence."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.incremental_opus_editor import (
    build_scene_spans, validate_patch, generate_single_scene_specs,
    parse_silencedetect, make_cut_plan, build_keep_plan, reusable_cache_key,
    spec_duration_frames,
)

ROOT=Path(__file__).resolve().parents[1]
BOARD=json.loads((ROOT/"video-requests/five-systems-original-opus-2026.json").read_text(encoding="utf-8"))
PATCH=json.loads((ROOT/"video-requests/five-systems-visual-fixes.json").read_text(encoding="utf-8"))

class IncrementalOpusTests(unittest.TestCase):
    def test_only_two_bad_scenes_selected(self):
        fixes=validate_patch(BOARD,PATCH)
        self.assertEqual(sorted(fixes),[7,8])
        self.assertEqual(fixes[7]["motion"],"notification-stack")
        self.assertEqual(fixes[7]["props"]["layout"],"list")
        self.assertEqual(fixes[8]["motion"],"device-mockup")
        self.assertEqual(fixes[8]["props"]["src"],"software/twenty/verified.png")

    def test_25_exact_scene_ranges_and_no_unrequested_redraw(self):
        spans=build_scene_spans(BOARD)
        self.assertEqual(len(spans),25)
        self.assertEqual(spans[0]["start_frame"],0)
        self.assertEqual(spans[-1]["end_frame"],9000)
        self.assertEqual([x["index"] for x in spans if x["index"] in PATCH["scene_overrides"]],[7,8])
        for a,b in zip(spans,spans[1:]):
            self.assertEqual(a["end_frame"],b["start_frame"])

    def test_direct_original_opus_single_scene_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            specs=generate_single_scene_specs(BOARD,PATCH,Path(tmp))
            self.assertEqual(set(specs),{7,8})
            for n,path in specs.items():
                spec=json.loads(path.read_text())
                self.assertEqual(len(spec["scenes"]),1)
                self.assertEqual(spec["scenes"][0]["motion"],PATCH["scene_overrides"][str(n)]["motion"])
                self.assertEqual(spec_duration_frames(spec),BOARD["scenes"][n-1]["min"])
                self.assertEqual(spec["audio"]["sfx"],[])
                self.assertEqual(spec["captions"],[])
                self.assertEqual(spec["scenes"][0]["transition"]["type"],"cut")

    def test_reject_rerendering_all_scenes_or_unrequested_mutations(self):
        bad=json.loads(json.dumps(PATCH))
        bad["scene_overrides"]["26"]={"motion":"stamp-slam","props":{}}
        with self.assertRaises(ValueError):validate_patch(BOARD,bad)
        bad=json.loads(json.dumps(PATCH))
        bad["scene_overrides"]["9"]={"motion":"nonexistent-motion","props":{}}
        with self.assertRaises(ValueError):validate_patch(BOARD,bad)
        bad=json.loads(json.dumps(PATCH))
        bad["scene_overrides"]["1"]=bad["scene_overrides"]["7"]
        with self.assertRaises(ValueError):validate_patch(BOARD,bad)

    def test_long_silences_cropped_in_audio_and_video_with_padding(self):
        text="""[silencedetect] silence_start: 2.000
[silencedetect] silence_end: 3.800 | silence_duration: 1.800
[silencedetect] silence_start: 8.300
[silencedetect] silence_end: 9.100 | silence_duration: 0.800"""
        ranges=parse_silencedetect(text,12.0)
        self.assertEqual(len(ranges),2)
        cuts=make_cut_plan(ranges,12.0,fps=30,min_gap=.65,pad=.18)
        self.assertEqual(len(cuts),2)
        keeps=build_keep_plan(cuts,360)
        self.assertEqual(keeps[0][0],0)
        self.assertEqual(keeps[-1][1],360)
        self.assertGreater(sum(b-a for a,b in keeps),0)
        self.assertLess(sum(b-a for a,b in keeps),360)
        self.assertTrue(all((a%1==0 and b%1==0 and b>a) for a,b in keeps))

    def test_short_pauses_and_speech_not_cut(self):
        ranges=[(1.0,1.31),(2.0,2.50)]
        self.assertFalse(make_cut_plan(ranges,3.0,min_gap=.65,pad=.18))
        self.assertEqual(build_keep_plan([],90),[(0,90)])

    def test_cache_reuses_exact_scene_only_when_source_and_encoding_same(self):
        one=reusable_cache_key("abc",7,120,360,"h264-30-crf21-v2")
        self.assertEqual(one,reusable_cache_key("abc",7,120,360,"h264-30-crf21-v2"))
        self.assertNotEqual(one,reusable_cache_key("abc",8,120,360,"h264-30-crf21-v2"))
        self.assertNotEqual(one,reusable_cache_key("abd",7,120,360,"h264-30-crf21-v2"))

    def test_workflow_renders_only_original_opus_scenes_seven_eight(self):
        w=(ROOT/".github/workflows/five-systems-incremental-fixes.yml").read_text()
        self.assertIn("cli/mgl.mjs compose",w)
        self.assertIn("scene_07.json",w)
        self.assertIn("scene_08.json",w)
        self.assertIn("actions/cache@v4",w)
        self.assertIn("node",w)
        self.assertIn("original artifact",w.lower())
        self.assertNotIn("cli/direct.mjs",w)
        self.assertNotIn("python -m scripts.full300_editor",w)

if __name__=="__main__":unittest.main()
