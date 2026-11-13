"""Compatibilidade entre versões do Misaki EspeakG2P (retorno texto ou tupla)."""
import unittest

from scripts.paradee_voice import phonemes_from_g2p_result


class EspeakResultCompatibilityTests(unittest.TestCase):
    def test_string_return_is_not_unpacked_by_character(self):
        self.assertEqual(phonemes_from_g2p_result("olˈa mundu"), "olˈa mundu")

    def test_two_element_tuple_returns_phoneme_string(self):
        self.assertEqual(phonemes_from_g2p_result(("olˈa mundu", None)), "olˈa mundu")

    def test_three_element_tuple_is_safe(self):
        self.assertEqual(phonemes_from_g2p_result(("olˈa mundu", None, None)), "olˈa mundu")

    def test_empty_or_invalid_return_fails_clearly(self):
        for result in ("", (), (None, None), None, 123):
            with self.subTest(result=result):
                with self.assertRaises(ValueError):
                    phonemes_from_g2p_result(result)


if __name__ == "__main__":
    unittest.main()
