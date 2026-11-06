"""Regressões: carrossel fotográfico gratuito, texto e entrega."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.render_carousel import (
    CarouselError, build_caption, choose_candidate, compose_carousel,
    parse_candidates, safe_photo_url, select_requests, validate_request,
)


def sample_slides():
    return [
        {"title": "4 sites para programar melhor", "body": "Salve este guia para consultar depois."},
        {"title": "Roadmap.sh", "body": "Trilhas para orientar seu estudo."},
        {"title": "Exercism", "body": "Exercícios de programação gratuitos."},
        {"title": "DevDocs", "body": "Documentação técnica em um só lugar."},
        {"title": "Regex101", "body": "Teste expressões regulares visualmente."},
        {"title": "Salve para depois", "body": "ArtiSys: tecnologia prática."},
    ]


def sample_candidate(license_url="https://creativecommons.org/licenses/by/4.0/",
                     host="https://upload.wikimedia.org/wikipedia/commons/a/ab/setup.jpg"):
    return {"query": {"pages": [{
        "title": "File:Modern desktop setup.jpg",
        "imageinfo": [{
            "url": host,
            "thumburl": host,
            "size": 1200000,
            "width": 2000,
            "height": 3000,
            "mediatype": "BITMAP",
            "extmetadata": {
                "LicenseUrl": {"value": license_url},
                "Artist": {"value": "<b>Example photographer</b>"}
            },
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Modern_desktop_setup.jpg",
        }]
    }]}}


class CarouselTests(unittest.TestCase):
    def test_minimal_request_is_free_and_reuses_one_photo(self):
        request = validate_request({"topic": "Ferramentas para programadores"})
        self.assertEqual(request["photo_mode"], "same")
        self.assertEqual(request["style"], "cinematic")
        self.assertEqual(request["slide_count"], 6)
        self.assertEqual(request["source"], "wikimedia")
        self.assertGreater(len(request["photo_terms"]), 0)

    def test_rejects_paid_and_unsafe_parameters(self):
        bad = [
            {"topic": ""},
            {"topic": "x", "source": "paid_ai"},
            {"topic": "x", "image_url": "https://evil.example/photo.jpg"},
            {"topic": "x", "photo_mode": "remote"},
            {"topic": "x", "slide_count": 15},
            {"topic": "x", "style": "script"},
            {"topic": "x", "slides": [{"title": "x", "body": "y"}]},
            {"topic": "x", "photo_terms": ["x\nbad"]},
            {"topic": "x", "slides": [{"title": "x"*200, "body": ""}]*6},
            {"topic": "x", "items": [{"name": "a", "url": "file:///etc/passwd"}]},
        ]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(CarouselError):
                validate_request(value)

    def test_explicit_six_slides_do_not_need_llm(self):
        req = validate_request({"topic": "4 sites gratuitos", "slides": sample_slides()})
        self.assertEqual(req["slides"], sample_slides())

    def test_only_open_licensed_photos_with_verified_metadata(self):
        records = parse_candidates(sample_candidate())
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["license"], "CC BY 4.0")
        self.assertEqual(records[0]["author"], "Example photographer")
        self.assertFalse(parse_candidates(sample_candidate(
            license_url="https://creativecommons.org/licenses/by-nc/4.0/")))
        self.assertFalse(parse_candidates(sample_candidate(
            host="https://attacker.example/wikipedia/commons/a.jpg")))
        self.assertFalse(safe_photo_url("http://upload.wikimedia.org/x.jpg"))
        self.assertFalse(safe_photo_url("https://upload.wikimedia.org.evil.com/p.jpg"))

    def test_prefers_large_portrait_photo(self):
        good = parse_candidates(sample_candidate())[0]
        bad = dict(good, width=600, height=300, title="File:Landscape.jpg",
                   url="https://upload.wikimedia.org/wikipedia/commons/b/bc/land.jpg")
        self.assertEqual(choose_candidate([bad, good])["url"], good["url"])

    def test_select_requests_is_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "carousel_requests").mkdir()
            (root / "carousel_requests/demo.json").write_text('{"topic":"ok"}')
            selected = select_requests(root, manual="carousel_requests/demo.json")
            self.assertEqual(selected, [root / "carousel_requests/demo.json"])
            for path in ("../secrets.json", "requests/demo.json",
                         "carousel_requests/../../passwd"):
                with self.subTest(path=path), self.assertRaises(CarouselError):
                    select_requests(root, manual=path)

    def test_compose_six_jpgs_caption_credits_and_zip(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "photo.jpg"
            Image.new("RGB", (1200, 1800), "#627a92").save(source)
            req = validate_request({"topic": "4 sites", "slides": sample_slides()})
            out = root / "output"
            item = parse_candidates(sample_candidate())[0]
            image_paths = compose_carousel(req, source, out, item)
            self.assertEqual(len(image_paths), 6)
            for path in image_paths:
                with Image.open(path) as im:
                    self.assertEqual(im.size, (1080, 1920))
                    self.assertEqual(im.format, "JPEG")
            self.assertTrue((out / "carrossel.zip").is_file())
            self.assertTrue((out / "creditos.txt").is_file())
            self.assertIn("creativecommons.org", (out / "creditos.txt").read_text())
            self.assertIn("Roadmap.sh", (out / "legenda.txt").read_text())
            with zipfile.ZipFile(out / "carrossel.zip") as archive:
                self.assertIn("01.jpg", archive.namelist())
                self.assertIn("06.jpg", archive.namelist())
                self.assertIn("legenda.txt", archive.namelist())
            with Image.open(image_paths[0]) as first, Image.open(image_paths[-1]) as last:
                self.assertEqual(first.getpixel((400, 300)), last.getpixel((400, 300)))

    def test_caption_uses_explicit_items_without_inventing_links(self):
        req = validate_request({
            "topic": "Ferramentas", "slides": sample_slides(),
            "items": [{"name": "DevDocs", "url": "https://devdocs.io", "detail": "Documentação"}]
        })
        caption = build_caption(req)
        self.assertIn("https://devdocs.io", caption)
        self.assertIn("DevDocs", caption)
        self.assertNotIn("pixabay", caption.lower())


if __name__ == "__main__":
    unittest.main()
