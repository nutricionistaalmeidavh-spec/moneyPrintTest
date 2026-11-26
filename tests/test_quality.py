import os
import unittest
from unittest.mock import patch

from scripts import quality
from scripts.animated_slides import SUPERSAMPLE, _background, make_slide


class QualityArgsTests(unittest.TestCase):
    def test_defaults_are_not_veryfast_crf23(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MONEYPRINT_X264_PRESET", None)
            os.environ.pop("MONEYPRINT_X264_CRF", None)
            args = quality.x264_args()
        self.assertEqual(args[args.index("-preset") + 1], "medium")
        self.assertEqual(args[args.index("-crf") + 1], "18")
        self.assertIn("bt709", args)
        self.assertIn("aq-mode=3", " ".join(args))

    def test_env_override_and_invalid_values_fall_back(self):
        with patch.dict(os.environ, {"MONEYPRINT_X264_PRESET": "veryfast",
                                     "MONEYPRINT_X264_CRF": "21"}):
            args = quality.x264_args()
        self.assertEqual(args[args.index("-preset") + 1], "veryfast")
        self.assertEqual(args[args.index("-crf") + 1], "21")
        with patch.dict(os.environ, {"MONEYPRINT_X264_PRESET": "bogus",
                                     "MONEYPRINT_X264_CRF": "999"}):
            args = quality.x264_args()
        self.assertEqual(args[args.index("-preset") + 1], "medium")
        self.assertEqual(args[args.index("-crf") + 1], "18")

    def test_intermediate_is_near_lossless(self):
        args = quality.intermediate_args()
        self.assertEqual(args[args.index("-crf") + 1], str(quality.INTERMEDIATE_CRF))


class BackgroundTests(unittest.TestCase):
    def test_gradient_is_dithered_not_flat_rows(self):
        im = _background((640, 360))
        # A banded gradient has identical pixels along every row; dithering
        # must make neighbouring pixels differ.
        row = [im.getpixel((x, 200)) for x in range(100, 140)]
        self.assertGreaterEqual(len(set(row)), 2)

    def test_slides_render_supersampled(self):
        import tempfile
        from pathlib import Path
        from PIL import Image
        section = {"repo_url": "https://github.com/a/b", "title": "B"}
        with tempfile.TemporaryDirectory() as tmp:
            out = make_slide(section, 1, 1, "benefit", Path(tmp) / "s.png",
                             size=(480 * SUPERSAMPLE, 270 * SUPERSAMPLE))
            with Image.open(out) as im:
                self.assertEqual(im.size, (480 * SUPERSAMPLE, 270 * SUPERSAMPLE))


if __name__ == "__main__":
    unittest.main()
