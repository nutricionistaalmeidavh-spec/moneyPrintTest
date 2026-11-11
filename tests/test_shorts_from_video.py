import tempfile
import unittest
from pathlib import Path
from scripts.shorts_from_video import choose_clips, validate_segments, write_captions, make_candidates, _time

class ShortsTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{"start": i * 5.0, "end": i * 5.0 + 4.8,
                      "text": ("Nuclei encontra vulnerabilidades no site." if i < 12 else
                               "O relatorio mostra riscos e correcoes." if i < 22 else
                               "Pentest responsavel precisa escopo autorizado."),
                      "words": []} for i in range(34)]

    def test_choose_multiple_coherent_nonoverlapping_clips(self):
        clips = choose_clips(self.rows, count=4, minimum=25, maximum=42)
        self.assertEqual(len(clips), 4)
        for clip in clips:
            self.assertGreaterEqual(clip["end"]-clip["start"], 25)
            self.assertLessEqual(clip["end"]-clip["start"], 42)
        for previous, current in zip(clips, clips[1:]):
            self.assertLessEqual(previous["end"], current["start"])

    def test_reject_out_of_order_or_missing_speech(self):
        with self.assertRaises(ValueError):
            validate_segments([{"start": 4, "end": 2, "text": "a"}], 10)
        with self.assertRaises(ValueError):
            validate_segments([{"start": 0, "end": 2, "text": ""}], 10)

    def test_long_silence_is_not_inside_candidate(self):
        rows = [{"start": 0, "end": 5, "text": "A."},
                {"start": 12, "end": 30, "text": "B."}]
        self.assertEqual(make_candidates(rows, 20, 40), [])

    def test_subtitles_are_mapped_to_short_local_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp)/"subtitle.ass"
            write_captions(file, [{"start": 10, "end": 14,
                "text": "Como fazer pentest gratuito com ferramentas abertas?", "words": []}],
                offset=10, length=4)
            text = file.read_text()
            self.assertIn("Dialogue: 0,0:00:00.", text)
            self.assertIn("PlayResX: 1080", text)
            self.assertIn("PlayResY: 1920", text)

    def test_time_format(self):
        self.assertEqual(_time(61.27), "0:01:01.27")

if __name__ == "__main__":
    unittest.main()
