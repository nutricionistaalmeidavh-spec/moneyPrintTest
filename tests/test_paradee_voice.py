"""Paradee PT-BR integration: original Opus visuals retained; narration replaced."""
import json
import unittest
from pathlib import Path

from scripts.paradee_voice import (
    MODEL_REPO, MODEL_REVISION, VOICE_FILES, AUDIO_RATE, make_tokens,
    split_text, visual_scene_ranges, silence_compact, design_visual_splice,
)

ROOT=Path(__file__).resolve().parents[1]
BOARD=json.loads((ROOT/"video-requests/five-systems-original-opus-2026.json").read_text())

class ParadeeVoiceTests(unittest.TestCase):
    def test_original_apache_onnx_model_pinned(self):
        self.assertEqual(MODEL_REPO,"eraldohug/Paradee-8M-PtBr")
        self.assertEqual(len(MODEL_REVISION),40)
        self.assertEqual(AUDIO_RATE,24000)
        self.assertEqual(VOICE_FILES["alex"],"onnx/paradee_alex_int8.onnx")
        self.assertEqual(VOICE_FILES["dora"],"onnx/paradee_dora_int8.onnx")

    def test_token_sequence_is_padded_and_valid(self):
        vocab={"a":3,"b":7," ":10,"?":12}
        ids=make_tokens("a b?",vocab)
        self.assertEqual(ids,[0,3,10,7,12,0])
        with self.assertRaises(ValueError):make_tokens("zzz",vocab)
        with self.assertRaises(ValueError):make_tokens("a"*513,vocab)

    def test_long_text_is_split_without_dropping_words(self):
        original=" ".join(["Integração entre vendas, estoque e financeiro."]*35)
        chunks=split_text(original,max_chars=150)
        self.assertGreater(len(chunks),5)
        self.assertEqual(" ".join(chunks),original)
        self.assertTrue(all(len(c)<=150 for c in chunks))

    def test_retains_all_25_canonical_original_opus_scenes(self):
        rows=visual_scene_ranges(BOARD)
        self.assertEqual(len(rows),25)
        self.assertEqual(rows[0]["start_frame"],0)
        self.assertEqual(rows[-1]["end_frame"],9000)
        self.assertTrue(all(a["end_frame"]==b["start_frame"] for a,b in zip(rows,rows[1:])))

    def test_silence_removes_dead_air_but_keeps_natural_short_pauses(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest('NumPy optional in global suite; installed by Paradee workflow')
        sr=24000
        tone=np.sin(np.arange(sr,dtype=np.float32)*2*np.pi*220/sr)*.22
        signal=np.concatenate([np.zeros(sr),tone,np.zeros(sr*2),tone,np.zeros(sr)],axis=0)
        clean,info=silence_compact(signal,sr,max_pause=.4)
        self.assertGreater(info["removed_seconds"],3)
        self.assertLess(len(clean)/sr,2.8)
        self.assertGreater(len(clean)/sr,2)

    def test_visual_splice_preserves_original_motions_no_reimplementation(self):
        rows=visual_scene_ranges(BOARD)
        new=[260 if r["index"]==1 else 330 for r in rows]
        graph=design_visual_splice(rows,new)
        self.assertEqual(graph["total_frames"],260+24*330)
        self.assertIn("trim=start_frame=0:end_frame=90",graph["filters"])
        self.assertIn("setpts=(PTS-STARTPTS)",graph["filters"])
        self.assertIn("concat=n=25",graph["filters"])
        self.assertNotIn("drawtext",graph["filters"])

    def test_misaki_pt_br_installs_its_runtime_phonemizer_explicitly(self):
        workflow=(ROOT/".github/workflows/five-systems-paradee-voice.yml").read_text()
        self.assertIn("phonemizer>=3.3,<4",workflow)
        self.assertIn("espeakng-loader",workflow)
        self.assertIn("from misaki.espeak import EspeakG2P",workflow)

    def test_workflow_uses_original_movie_and_never_rerenders_react(self):
        w=(ROOT/".github/workflows/five-systems-paradee-voice.yml").read_text()
        self.assertIn("43040474562",w)
        self.assertIn("onnxruntime",w)
        self.assertIn("espeakng-loader",w)
        self.assertIn("scripts.paradee_voice",w)
        self.assertIn("actions/download-artifact",w)
        self.assertNotIn("cli/direct.mjs",w)
        self.assertNotIn("remotion render",w)
        self.assertNotIn("sudo apt-get",w)
        self.assertNotIn("apt-get update",w)
        self.assertNotIn("apt-get install",w)
        self.assertNotIn("qwen-tts",w)

if __name__=="__main__":unittest.main()
