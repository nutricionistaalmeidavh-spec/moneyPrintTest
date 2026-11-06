import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.pixabay_carousel import (
    validate_job, score_hit, select_candidates, build_text_lines,
    source_photo_url, safe_photo_url, render_slides
)


def stock_hit(photo_id=111, tags="breast milk, breast pump, baby, mother",
              h=2048, w=1300, views=100):
    return {
        "id": photo_id, "tags": tags, "imageWidth": w, "imageHeight": h,
        "views": views, "downloads": 13, "user": "Contributor",
        "pageURL": f"https://pixabay.com/photos/stock-{photo_id}/",
        "webformatURL": f"https://cdn.pixabay.com/photo/test-{photo_id}_1280.jpg",
        "largeImageURL": f"https://cdn.pixabay.com/photo/test-{photo_id}_1920.jpg",
    }


class PixabayCarouselTests(unittest.TestCase):
    def test_accepts_only_safe_publish_fields(self):
        job = validate_job({"topic": "Peito mais macio", "searches": ["breast pump"],
                            "texts": ["Primeiro slide"] * 5})
        self.assertEqual(job["texts"][0], "Primeiro slide")
        self.assertIsNone(job["photo_id"])
        with self.assertRaises(ValueError):
            validate_job({"topic": "x", "searches": ["bottle"], "texts": ["a"] * 5,
                          "webhook": "https://example.com"})
        with self.assertRaises(ValueError):
            validate_job({"topic": "x", "searches": ["bottle"], "texts": ["a"] * 4})

    def test_real_breastmilk_stock_beats_generic_cow_milk(self):
        lactation = stock_hit()
        cow = stock_hit(222, "cow, milk, cattle, farm", views=100000)
        self.assertGreater(score_hit(lactation), score_hit(cow))
        picks = select_candidates([cow, lactation])
        self.assertEqual(picks[0]["id"], 111)

    def test_rejects_untrusted_photo_hosts(self):
        self.assertTrue(safe_photo_url(source_photo_url(stock_hit())))
        self.assertFalse(safe_photo_url("https://attacker.example/bad.jpg"))
        self.assertFalse(safe_photo_url("http://cdn.pixabay.com/bad.jpg"))
        self.assertFalse(safe_photo_url("https://pixabay.com.evil.example/1.jpg"))

    def test_no_blurred_or_opacity_background_for_text(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = Image.new("RGB", (1200, 1900), (115, 139, 166))
            src = root / "source.jpg"
            original.save(src)
            job = validate_job({"topic": "Peito mais macio",
                                "searches": ["breast pump"], "texts": [
                                    "PEITO MAIS MACIO?",
                                    "O CORPO SE ADAPTA.",
                                    "PEITO CHEIO NÃO É MEDIDOR.",
                                    "OBSERVE O BEBÊ.",
                                    "SIGA @DEBORA.LACTACAO"
                                ]})
            outs = render_slides(src, root, job)
            self.assertEqual(len(outs), 5)
            slide = Image.open(outs[0]).convert("RGB")
            self.assertEqual(slide.size, (1080, 1920))
            # JPEG da foto de teste tem pequenas variações de compressão.
            for x, y in [(10, 800), (1050, 900)]:
                pixel = slide.getpixel((x, y))
                self.assertTrue(all(abs(a - b) <= 5 for a, b in zip(pixel, (115, 139, 166))))
            # Text is stroked, but no blurred cards/panels may paint the rest.
            self.assertNotEqual(slide.getpixel((540, 1050)), (255, 247, 232))

    def test_wraps_long_portuguese_text_for_phone(self):
        from PIL import ImageDraw, ImageFont, Image
        draw = ImageDraw.Draw(Image.new("RGB", (1080,1920)))
        ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 65)
        lines = build_text_lines(draw, "A PRODUÇÃO SE AJUSTA ÀS NECESSIDADES DO SEU BEBÊ", ft, 920)
        self.assertGreater(len(lines), 1)
        self.assertTrue(all(draw.textbbox((0,0),l,font=ft)[2] <= 920 for l in lines))


if __name__ == "__main__":
    unittest.main()
