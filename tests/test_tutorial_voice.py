"""Tests for free, offline narrator mix decisions."""
import unittest
from scripts.tutorial_voice import speech_tempo

class NarratorTests(unittest.TestCase):
    def test_normal_speech_gets_energetic_pacing(self):
        self.assertEqual(speech_tempo(18,24.8),1.0)
    def test_longer_speech_is_fitted_without_truncation(self):
        with self.assertRaisesRegex(ValueError,"longa demais"):
            speech_tempo(28,24.8)
    def test_invalid_timing_rejected(self):
        for args in ((0,25,1),(24,0,1),(10,20,21)):
            with self.assertRaises(ValueError):
                speech_tempo(*args)
if __name__=="__main__":
    unittest.main()
