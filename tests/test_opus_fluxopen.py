"""Contrato do vídeo FluxOpen: somente motions originais e 300 s de timeline."""
import json
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "video-requests/fluxopen-pentest-20261110.json"
APPROVED = {
    "stamp-slam", "mask-rise-title", "board-camera", "cause-effect-chain",
    "form-fill-submit", "network-graph", "radial-blueprint", "flow-diagram",
    "target-lock-box", "code-diff-highlight", "glass-lesson-card",
    "counting-objects", "ken-burns", "document-zoom-highlight",
    "deploy-pipeline-stages", "api-request-flow", "chat-bubbles",
    "end-screen-cards", "number-counter"
}
class FluxOpenOpusTest(unittest.TestCase):
    def test_25_scenes_and_five_minutes(self):
        movie = json.loads(SOURCE.read_text(encoding="utf-8"))
        self.assertEqual(len(movie["scenes"]), 25)
        self.assertEqual(movie["fps"], 30)
        self.assertEqual((movie["width"], movie["height"]), (1920, 1080))
        self.assertEqual(sum(s["min"] for s in movie["scenes"]), 9000)

    def test_original_motions_and_narration(self):
        movie = json.loads(SOURCE.read_text(encoding="utf-8"))
        self.assertFalse(movie["captions"])
        self.assertEqual(movie["name"], "fluxopen-pentest-gratuito")
        for s in movie["scenes"]:
            self.assertIn(s["motion"], APPROVED)
            self.assertIsInstance(s.get("say"), str)
            self.assertGreater(len(s["say"].split()), 13)
            self.assertEqual(s["transition"]["type"], "cut")
            self.assertNotIn("tag", s)
        used={s["motion"] for s in movie["scenes"]}
        for must in ("board-camera","cause-effect-chain","code-diff-highlight","end-screen-cards","ken-burns"):
            self.assertIn(must,used)

if __name__ == "__main__":
    unittest.main()
