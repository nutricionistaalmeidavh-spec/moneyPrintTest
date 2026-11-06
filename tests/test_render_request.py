import tempfile
import unittest
from pathlib import Path

from scripts.render_request import (
    RequestError, validate_request, select_visual_mode,
    select_requests, build_config, build_manifest, clean_terms,
    redact_log, local_slides, normalize_generated_terms, acceptable_script, target_word_count,
)


class RenderTests(unittest.TestCase):
    def test_only_topic_is_valid(self):
        request = validate_request({"topic": "Como usar ferramentas open source"})
        self.assertEqual(request["visual_mode"], "auto")
        self.assertEqual(request["aspect"], "9:16")

    def test_dangerous_or_expensive_parameters_are_denied(self):
        for request in [
            {"topic": ""},
            {"topic": "x", "visual_mode": "paid_video"},
            {"topic": "x", "duration_seconds": 9999},
            {"topic": "x", "terms": ["good", "bad\nterm"]},
            {"topic": "x", "secret": "should-not-be-accepted"},
        ]:
            with self.subTest(request=request), self.assertRaises(RequestError):
                validate_request(request)

    def test_free_stock_and_offline_fallback(self):
        self.assertEqual(select_visual_mode("auto", {}), "wikimedia")
        self.assertEqual(select_visual_mode("stock", {}), "wikimedia")
        self.assertEqual(select_visual_mode("auto", {"PEXELS_API_KEY": "abc"}), "wikimedia")
        self.assertEqual(select_visual_mode("local", {}), "local")
        self.assertEqual(select_visual_mode("pexels", {"PEXELS_API_KEY": "abc"}), "pexels")
        with self.assertRaisesRegex(RequestError, "pexels"):
            select_visual_mode("pexels", {})

    def test_paths_cannot_escape_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "requests").mkdir()
            (root / "requests/one.json").write_text('{"topic":"x"}')
            self.assertEqual(select_requests(root, manual="requests/one.json"),
                             [root / "requests/one.json"])
            for unsafe in ("../test.json", "README.md", "requests/../../x.json"):
                with self.subTest(unsafe=unsafe), self.assertRaises(RequestError):
                    select_requests(root, manual=unsafe)

    def test_config_never_activates_a_paid_provider(self):
        config = build_config({"app": {"llm_provider": "moonshot"}, "whisper": {}},
                              {"PEXELS_API_KEY": "testing"})
        self.assertEqual(config["app"]["llm_provider"], "ollama")
        self.assertEqual(config["app"]["pexels_api_keys"], ["testing"])
        self.assertEqual(config["app"]["subtitle_provider"], "whisper")
        self.assertEqual(config["whisper"]["model_size"], "tiny")

    def test_manifest_uses_only_local_voice_and_no_paid_music(self):
        request = validate_request({"topic": "Ferramentas gratuitas"})
        result = build_manifest(request, "Meu roteiro", ["technology"], "local",
                                "/tmp/voice.wav", ["/tmp/a.jpg"])
        self.assertEqual(result["voice_name"], "no-voice")
        self.assertEqual(result["bgm_type"], "")
        self.assertEqual(result["custom_audio_file"], "/tmp/voice.wav")
        self.assertEqual(result["video_materials"][0]["provider"], "local")

    def test_llm_terms_are_normalized_without_rejecting_topic(self):
        self.assertEqual(
            normalize_generated_terms(["business\nsoftware", {}, "company finance  "], "x"),
            ["business software", "company finance"],
        )
        self.assertTrue(normalize_generated_terms(None, "My topic"))

    def test_term_limits(self):
        self.assertEqual(clean_terms([" open source ", "management", "open source"]),
                         ["open source", "management"])
        with self.assertRaises(RequestError):
            clean_terms(["a" * 1000])

    def test_secrets_do_not_leak_into_artifacts(self):
        self.assertEqual(redact_log("key=abc123", {"PEXELS_API_KEY": "abc123"}),
                         "key=[REDACTED]")

    def test_roteiro_curto_e_metaliguagem_rejeitados(self):
        self.assertEqual(target_word_count(30), 75)
        self.assertFalse(acceptable_script("O script aborda ferramentas gratuitas.", 30))
        self.assertFalse(acceptable_script("software " * 20, 30))
        self.assertTrue(acceptable_script("Use soluções abertas e faça testes antes de decidir. " * 9, 30))

    def test_local_media_exists(self):
        try:
            import PIL
        except ImportError:
            self.skipTest("Pillow não instalado")
        with tempfile.TemporaryDirectory() as temp:
            media = local_slides("Obras abertas", Path(temp), "9:16")
            self.assertEqual(len(media), 3)
            self.assertTrue(all(Path(file).stat().st_size > 1000 for file in media))


if __name__ == "__main__":
    unittest.main()
