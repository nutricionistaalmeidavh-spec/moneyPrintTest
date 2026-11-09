"""Native MoneyPrinterTurbo voice integration: no external TTS fallback."""
import tempfile
import unittest
from pathlib import Path

from scripts.tutorial_mpt_voice import VoiceError, validate_request, synthesize

class NativeMptVoiceTests(unittest.TestCase):
    def test_local_kokoro_voice_selected_by_default(self):
        params = validate_request("Texto para narrar.", "kokoro:pm_alex", 1.08, "http://127.0.0.1:8880/v1")
        self.assertEqual(params["voice"], "kokoro:pm_alex")
        self.assertEqual(params["endpoint"], "http://127.0.0.1:8880/v1")

    def test_no_cloud_automatic_fallback_or_paid_provider(self):
        for provider in ["pt-BR-AntonioNeural", "elevenlabs:123", "chatterbox:random", "kokoro:af_heart"]:
            with self.subTest(provider=provider), self.assertRaises(VoiceError):
                validate_request("Narrou",provider,1.08,"http://127.0.0.1:8880/v1")
        for endpoint in ["https://api.openai.com/v1", "http://evil.test/v1",
                         "http://localhost:443/v1","http://127.0.0.1:8880/v2"]:
            with self.subTest(endpoint=endpoint),self.assertRaises(VoiceError):
                validate_request("Teste","kokoro:pm_alex",1.08,endpoint)

    def test_rejects_gimmicky_fast_speech_and_empty_script(self):
        for script,rate in [("",1.0),("script",1.7),("narrador",0.6)]:
            with self.assertRaises(VoiceError):
                validate_request(script,"kokoro:pm_alex",rate,"http://127.0.0.1:8880/v1")

    def test_calls_actual_moneyprinterturbo_tts_function(self):
        with tempfile.TemporaryDirectory() as root:
            out=Path(root)/"voice.mp3"
            cfg={}
            calls=[]
            def native(text, voice_name, voice_rate, voice_file, voice_volume):
                calls.append((text,voice_name,voice_rate,voice_file,voice_volume))
                Path(voice_file).write_bytes(b"ID3"+b"f"*4096)
                return object()
            result = synthesize("Primeiro repositorio",out,tts_callable=native,kokoro_config=cfg)
            self.assertEqual(result["provider"],"moneyprinterturbo:k okoro".replace(" ",""))
            self.assertEqual(calls[0][1],"kokoro:pm_alex")
            self.assertEqual(cfg["model_id"],"kokoro")

    def test_failure_does_not_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(VoiceError,"MoneyPrinterTurbo"):
                synthesize("Primeiro repositorio",Path(root)/"voice.mp3",
                           tts_callable=lambda *args,**kwargs: None,kokoro_config={})

if __name__=="__main__":
    unittest.main()
