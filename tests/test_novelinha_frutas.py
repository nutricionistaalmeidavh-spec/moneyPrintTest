"""Contratos para storyboard da novelinha Frutalândia (sem serviços pagos)."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.novelinha_frutas import StoryError, compile_story, emit_plan, validate_story, check_voice_studio_url

FIXTURE = Path(__file__).resolve().parents[1] / "stories/frutalandia/audio-do-amanha-ep01.json"


class StoryTest(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_characters_and_continuity(self):
        story = validate_story(self.raw)
        self.assertEqual({x["id"] for x in story["characters"]},
                         {"moranguete", "uva", "mae-pera", "pai-caju"})
        self.assertEqual(sum(s["seconds"] for s in story["scenes"]), 48)

    def test_broken_speaker_rejected(self):
        self.raw["scenes"][0]["dialogue"][0]["speaker"] = "personagem-falso"
        with self.assertRaisesRegex(StoryError, "personagem"):
            validate_story(self.raw)

    def test_paid_provider_is_blocked(self):
        self.raw["policies"]["paid_providers"] = True
        with self.assertRaisesRegex(StoryError, "pago"):
            validate_story(self.raw)

    def test_auto_publish_is_blocked(self):
        self.raw["policies"]["auto_publish"] = True
        with self.assertRaisesRegex(StoryError, "publica"):
            validate_story(self.raw)

    def test_no_bare_script_or_placeholder_render(self):
        result = compile_story(validate_story(self.raw))
        self.assertEqual(result["openmontage"]["pipeline"], "character-animation")
        self.assertEqual(result["openmontage"]["render_runtime"], "hyperframes")
        self.assertEqual(len(result["voices"]), 6)
        self.assertNotIn("video_file", result)
        self.assertFalse(result["production_status"]["rendered"])

    def test_voice_endpoint_must_be_local(self):
        self.assertEqual(check_voice_studio_url("http://127.0.0.1:3900"), "http://127.0.0.1:3900")
        with self.assertRaises(StoryError):
            check_voice_studio_url("https://random.example/api")

    def test_emit_artifacts(self):
        compiled = compile_story(validate_story(self.raw))
        with tempfile.TemporaryDirectory() as d:
            emit_plan(compiled, Path(d))
            self.assertTrue((Path(d) / "openmontage-brief.json").exists())
            self.assertTrue((Path(d) / "voicestudio-lines.json").exists())
            self.assertTrue((Path(d) / "character-bible.json").exists())
            self.assertFalse(list(Path(d).glob("*.mp4")))


if __name__ == "__main__":
    unittest.main()
