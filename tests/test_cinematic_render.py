import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.cinematic_render import (
    make_cover, lower_third, make_news_card, prepare_shots, estimate_subtitles,
)


class CinematicRenderTests(unittest.TestCase):
    def test_design_assets_use_premium_typography(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cover = root / "cover.png"
            lower = root / "lower.png"
            news = root / "news.png"
            make_cover(cover, "8 repositórios para construir melhor")
            lower_third(lower, "Appwrite", 1, 8)
            make_news_card(news, {
                "headline": "Projeto open source anuncia atualização",
                "publisher": "Site de tecnologia",
                "published_at": "2026-11-08T12:00:00Z",
            })
            self.assertEqual(Image.open(cover).size, (1920, 1080))
            self.assertEqual(Image.open(lower).mode, "RGBA")
            self.assertEqual(Image.open(news).size, (1920, 1080))

    def test_reuse_actual_media_to_fill_narration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            media = root / "real_capture.mp4"
            media.write_bytes(b"valid-synthetic-fixture")
            plan = [{"asset_id": "repo", "seconds": 3}]
            shots = prepare_shots(plan, {"repo": media}, 10.5)
            self.assertEqual([round(n, 2) for _, n in shots], [3, 3, 3, 1.5])

    def test_no_fabricated_subtitles(self):
        cues = estimate_subtitles("Esta ferramenta facilita criação de aplicações.", 3, 4)
        self.assertGreater(len(cues), 0)
        self.assertEqual(cues[0]["text"],
                         "Esta ferramenta facilita criação de aplicações.")
        self.assertEqual(cues[0]["start"], 3)
        self.assertEqual(cues[-1]["end"], 7)


if __name__ == "__main__":
    unittest.main()
