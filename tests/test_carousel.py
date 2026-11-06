"""Regressões: carrossel fotográfico gratuito, texto e entrega."""
import json
import io
from unittest.mock import patch
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.render_carousel import (
    CarouselError, build_caption, choose_candidate, compose_carousel,
    parse_candidates, parse_pixabay_candidates, safe_photo_url, select_requests, validate_request,
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
        self.assertEqual(request["style"], "reference")
        self.assertEqual(request["aspect"], "4:5")
        self.assertEqual(request["slide_count"], 6)
        self.assertEqual(request["source"], "auto")
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

    def test_pixabay_free_photo_metadata_and_untrusted_host(self):
        sample = {"hits": [{
            "id": 144, "type": "photo", "user": "FotoAutor",
            "tags": "cozy desk setup", "imageWidth": 2100, "imageHeight": 1600,
            "pageURL": "https://pixabay.com/photos/desk-144/",
            "largeImageURL": "https://pixabay.com/get/modern_desktop_1280.jpg",
        }]}
        result = parse_pixabay_candidates(sample)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["provider"], "Pixabay")
        self.assertEqual(result[0]["license"], "Pixabay Content License")
        sample["hits"][0]["largeImageURL"] = "https://example.invalid/desk.jpg"
        self.assertEqual(parse_pixabay_candidates(sample), [])

    def test_prefers_large_portrait_photo(self):
        good = parse_candidates(sample_candidate())[0]
        bad = dict(good, width=600, height=300, title="File:Landscape.jpg",
                   url="https://upload.wikimedia.org/wikipedia/commons/b/bc/land.jpg")
        self.assertEqual(choose_candidate([bad, good])["url"], good["url"])

    def test_prefers_minimal_daylight_setups_over_game_screens(self):
        original = parse_candidates(sample_candidate())[0]
        gaming = dict(original, title="gamer 3d neon console playstation",
                      width=2400, height=3400)
        daylight = dict(original, title="minimalist home office desk daylight laptop",
                        width=1500, height=1700,
                        url="https://upload.wikimedia.org/wikipedia/commons/a/ab/office.jpg")
        self.assertEqual(choose_candidate([gaming, daylight])["title"],
                         daylight["title"])

    def test_full_workstation_ranks_above_laptop_and_notebook_closeup(self):
        from scripts.carousel_media import photo_score
        info = parse_candidates(sample_candidate())[0]
        closeup = dict(info, title="desk, laptop, notebook, pen, workplace, home office",
                       width=2200, height=3200)
        workstation = dict(info, title="office desk setup monitor keyboard laptop window plants",
                           width=1600, height=1600)
        self.assertGreater(photo_score(workstation), photo_score(closeup))

    def test_local_ollama_generates_six_pages_without_external_api(self):
        from scripts.render_carousel import _generate_slides_with_local_llm
        req = validate_request({"topic": "Boas práticas de programação"})
        fake = {"response": json.dumps({"slides": sample_slides()})}
        with patch("scripts.render_request.start_ollama", return_value=False):
            with patch("scripts.render_carousel.urlopen",
                       return_value=io.BytesIO(json.dumps(fake).encode())):
                result = _generate_slides_with_local_llm(req)
        self.assertEqual(len(result), 6)
        self.assertEqual(result[1]["title"], "Roadmap.sh")

    def test_rerender_single_page_preserves_page_number(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            photo = root / "background.jpg"
            Image.new("RGB", (1000, 1600), "#556678").save(photo)
            req = validate_request({"topic": "4 sites", "slides": sample_slides(),
                                    "only_pages": [3]})
            out = root / "out"
            rendered = compose_carousel(req, photo, out,
                                        parse_candidates(sample_candidate())[0])
            self.assertEqual([p.name for p in rendered], ["03.jpg"])
            with zipfile.ZipFile(out / "carrossel.zip") as archive:
                self.assertIn("03.jpg", archive.namelist())
                self.assertNotIn("01.jpg", archive.namelist())
            with self.assertRaises(CarouselError):
                validate_request({"topic": "x", "only_pages": [7]})

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

    def test_reference_layout_keeps_photo_visible_and_text_centered(self):
        from PIL import Image
        from scripts.render_carousel import _cover, _make_page
        with tempfile.TemporaryDirectory() as tmp:
            photo = Path(tmp) / "setup.jpg"
            Image.new("RGB", (1080, 1350), (180, 205, 210)).save(photo)
            req = validate_request({"topic": "Teste", "slides": sample_slides()})
            background = _cover(photo, req["aspect"])
            result = _make_page(background, req["slides"][0], req, 1, 6)
            self.assertEqual(result.size, (1080, 1350))
            # No top branding, bottom navigation, or full-photo dark gradient.
            for p in [(25, 25), (520, 90), (24, 1280), (520, 1300)]:
                self.assertEqual(background.getpixel(p), result.getpixel(p))
            # Reference-style headline is composited in central zone.
            difference = sum(background.getpixel((x, y)) != result.getpixel((x, y))
                             for y in range(400, 1050, 40)
                             for x in range(110, 1000, 40))
            self.assertGreater(difference, 10)

    def test_reference_accepts_9by16_but_legacy_preserves_old_aspect(self):
        self.assertEqual(validate_request({"topic": "x", "aspect": "9:16"})["aspect"], "9:16")
        self.assertEqual(validate_request({"topic": "x", "style": "cinematic"})["aspect"], "9:16")
        with self.assertRaises(CarouselError):
            validate_request({"topic": "x", "aspect": "3:2"})

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
                    self.assertEqual(im.size, (1080, 1350))
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
