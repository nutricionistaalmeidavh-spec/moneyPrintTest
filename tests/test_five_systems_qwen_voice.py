"""Regression suite: the original Opus video gets the real Qwen voice, not Piper."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class QwenOriginalVoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.five_systems_qwen_voice import build_timeline, REFERENCE_NAME
        cls.board=json.loads((ROOT/"video-requests/five-systems-original-opus-2026.json").read_text(encoding="utf-8"))
        cls.build_timeline=build_timeline
        cls.reference=REFERENCE_NAME

    def test_reference_is_original_qwen_sample(self):
        self.assertEqual(self.reference,"01_jovem_dinamico")
        workflow=(ROOT/".github/workflows/five-systems-qwen-voice.yml").read_text(encoding="utf-8")
        self.assertIn("moneyprint-qwen3-ptbr-preview-43047161887",workflow)
        self.assertIn("moneyprint-five-systems-opus-original",workflow)
        self.assertIn("43040474562",workflow)
        self.assertIn("qwen-tts==0.1.1",workflow)
        self.assertIn("actions/download-artifact",workflow)

    def test_timeline_uses_exact_25_opus_scenes_and_new_audio_times(self):
        seconds=[8.2]+[9.5]*24
        rows=type(self).build_timeline(self.board,seconds)
        self.assertEqual(len(rows),25)
        self.assertEqual(sum(row["original_frames"] for row in rows),9000)
        self.assertEqual(rows[0]["start_frame"],0)
        self.assertEqual(rows[-1]["end_frame"],9000)
        self.assertEqual(rows[0]["new_frames"],246)
        self.assertAlmostEqual(rows[-1]["video_end_seconds"],sum(row["new_frames"] for row in rows)/30)
        self.assertTrue(all(rows[i]["end_frame"]==rows[i+1]["start_frame"] for i in range(24)))
        self.assertTrue(all(row["text"]==original["say"] for row,original in zip(rows,self.board["scenes"])))

    def test_audio_is_not_recreated_from_existing_piper_track(self):
        runner=(ROOT/".github/workflows/five-systems-qwen-voice.yml").read_text(encoding="utf-8")
        script=(ROOT/"scripts/five_systems_qwen_voice.py").read_text(encoding="utf-8")
        self.assertIn("create_voice_clone_prompt",script)
        self.assertIn("generate_voice_clone",script)
        self.assertIn("Qwen/Qwen3-TTS-12Hz-0.6B-Base",script)
        self.assertIn("compact_silence",script)
        self.assertIn("setpts",script)
        self.assertIn("libx264",script)
        self.assertNotIn("scripts.full300_editor",runner)
        self.assertNotIn("piper-tts",runner)
        self.assertNotIn("python -m scripts.opus_motion_adapter",runner)

    def test_no_original_motion_mutations(self):
        workflow=(ROOT/".github/workflows/five-systems-qwen-voice.yml").read_text(encoding="utf-8")
        self.assertNotIn("git push",workflow)
        self.assertNotIn("npm install",workflow)
        self.assertNotIn("cli/direct.mjs",workflow)
        self.assertIn("concurrency:",workflow)
        self.assertIn("autopublish", (ROOT/"scripts/five_systems_qwen_voice.py").read_text(encoding="utf-8"))

    def test_silence_compactor_preserves_signal_and_removes_long_gaps(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest('NumPy optional in global tests; dedicated Qwen workflow installs it')
        from scripts.five_systems_qwen_voice import compact_silence
        sr=24000
        t=np.arange(sr,dtype=np.float32)/sr
        a=np.sin(t*2*np.pi*220)*.2
        signal=np.concatenate([np.zeros(sr,dtype=np.float32),a,
                               np.zeros(2*sr,dtype=np.float32),a,
                               np.zeros(sr,dtype=np.float32)])
        fixed,stats=compact_silence(signal,sr,max_pause=.23)
        self.assertGreater(stats["removed_seconds"],3.0)
        self.assertGreater(float(np.max(np.abs(fixed))),.15)
        self.assertLess(len(fixed)/sr,2.8)
        self.assertGreater(len(fixed)/sr,2.05)

if __name__=="__main__":unittest.main()
