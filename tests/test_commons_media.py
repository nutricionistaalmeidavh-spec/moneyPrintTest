"""Testes isolados do modo sem chave de API."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.commons_media import (
    CommonsError, approved_license, parse_candidates, source_credits,
    find_free_videos, fetch_file, api_search,
)


def candidate(license_url="https://creativecommons.org/licenses/by/4.0/",
              media_type="VIDEO", host="upload.wikimedia.org"):
    return {
        "title": "File:Test footage.webm",
        "imageinfo": [{
            "url": f"https://{host}/wikipedia/commons/a/ab/Test_footage.webm",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Test_footage.webm",
            "mediatype": media_type,
            "size": 200000,
            "extmetadata": {
                "LicenseUrl": {"value": license_url},
                "Artist": {"value": "<span>Author <b>Name</b></span>"},
            },
        }],
    }


class CommonsTests(unittest.TestCase):
    def test_allows_only_cc0_and_by_no_nc_no_sa(self):
        self.assertEqual(approved_license("https://creativecommons.org/licenses/by/4.0/")[0],
                         "CC BY 4.0")
        self.assertEqual(approved_license("https://creativecommons.org/publicdomain/zero/1.0/")[0],
                         "CC0 1.0")
        self.assertIsNone(approved_license("https://creativecommons.org/licenses/by-sa/4.0/"))
        self.assertIsNone(approved_license("https://creativecommons.org/licenses/by-nc/4.0/"))
        self.assertIsNone(approved_license("http://creativecommons.org/licenses/by/4.0/"))
        self.assertIsNone(approved_license("https://evil.example/licenses/by/4.0/"))

    def test_excludes_wrong_media_and_unsafe_origins(self):
        self.assertEqual(len(parse_candidates({"query": {"pages": [candidate()]}})), 1)
        for item in [
            candidate(media_type="BITMAP"),
            candidate(host="attacker.example"),
            candidate(license_url="https://creativecommons.org/licenses/by-sa/4.0/"),
        ]:
            with self.subTest(item=item):
                self.assertEqual(parse_candidates({"query": {"pages": [item]}}), [])

    def test_requires_credit_for_cc_by(self):
        item = candidate()
        item["imageinfo"][0]["extmetadata"]["Artist"]["value"] = ""
        self.assertEqual(parse_candidates({"query": {"pages": [item]}}), [])

    def test_credit_export_contains_author_license_and_modification(self):
        record = parse_candidates({"query": {"pages": [candidate()]}})[0]
        credits = source_credits([record])
        self.assertIn("Author Name", credits)
        self.assertIn("CC BY 4.0", credits)
        self.assertIn("Alterações: corte", credits)
        self.assertIn("https://commons.wikimedia.org", credits)

    def test_rejects_any_non_wikimedia_download_url(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(CommonsError):
                fetch_file("https://malicious.example/video.webm", Path(folder) / "test.webm")

    def test_mocked_stock_retrieval_stores_credits(self):
        record = parse_candidates({"query": {"pages": [candidate()]}})[0]
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root)
            def fake_download(url, target):
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"webm")
            def fake_transcode(source, target):
                target.write_bytes(b"\x00" * 8000)
            with patch("scripts.commons_media.api_search", return_value=[record]), \
                 patch("scripts.commons_media.fetch_file", side_effect=fake_download), \
                 patch("scripts.commons_media.transcode_video", side_effect=fake_transcode), \
                 patch("scripts.commons_media.time.sleep"):
                paths, sources = find_free_videos(["open source"], dest)
            self.assertEqual(len(paths), 1)
            self.assertEqual(len(sources), 1)
            self.assertTrue((dest / "creditos.txt").is_file())
            self.assertTrue((dest / "licencas_midia.json").is_file())
            self.assertEqual(json.loads((dest / "licencas_midia.json").read_text())[0]["author"],
                             "Author Name")

    def test_no_match_returns_empty_to_enable_local_fallback(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch("scripts.commons_media.api_search", return_value=[]), \
             patch("scripts.commons_media.time.sleep"):
            paths, sources = find_free_videos(["no results"], Path(tmp))
            self.assertEqual(paths, [])
            self.assertEqual(sources, [])


if __name__ == "__main__":
    unittest.main()
