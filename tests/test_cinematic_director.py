import unittest

from scripts.ai_director import (
    validate_sections, validate_director_plan, build_fallback_plan,
    canonical_news_record, approved_github_media_url,
)
from scripts.render_request import validate_request, RequestError


class CinematicDirectorTests(unittest.TestCase):
    def setUp(self):
        self.urls = [
            "https://github.com/appwrite/appwrite",
            "https://github.com/payloadcms/payload",
        ]
        self.sections = [
            {"repo_url": self.urls[0], "title": "Appwrite",
             "narration": "Um backend pronto para aplicativos modernos."},
            {"repo_url": self.urls[1], "title": "Payload",
             "narration": "Um CMS completo e extensível."}
        ]

    def test_cinematic_request_requires_mapped_sections(self):
        request = validate_request({
            "topic": "Repositórios open source", "visual_mode": "github_cinematic",
            "duration_seconds": 300, "aspect": "16:9",
            "repo_urls": self.urls, "sections": self.sections,
        })
        self.assertEqual(len(request["sections"]), 2)
        self.assertEqual(request["visual_mode"], "github_cinematic")
        with self.assertRaises(RequestError):
            validate_request({
                "topic": "x", "visual_mode": "github_cinematic",
                "repo_urls": self.urls, "sections": self.sections[:1]
            })

    def test_old_mode_forbids_cinematic_sections(self):
        with self.assertRaises(RequestError):
            validate_request({"topic": "x", "visual_mode": "github",
                              "repo_urls": self.urls, "sections": self.sections})
        with self.assertRaises(RequestError):
            validate_request({"topic": "x", "visual_mode": "auto",
                              "sections": self.sections})

    def test_news_sources_need_real_url_date_and_provenance(self):
        good = {"headline": "New open source tools for teams",
                "publisher": "GitHub Blog", "url": "https://github.blog/news/",
                "published_at": "2026-11-01T12:00:00Z"}
        self.assertIsNotNone(canonical_news_record(good))
        self.assertIsNone(canonical_news_record({**good, "url": "http://127.0.0.1/" }))
        self.assertIsNone(canonical_news_record({**good, "headline": "" }))
        self.assertIsNone(canonical_news_record({**good, "published_at": "" }))

    def test_model_may_only_choose_verified_asset_identifiers(self):
        approved = {"repo_1", "commons_1", "news_1"}
        self.assertEqual(validate_director_plan(
            {"shots": [{"asset_id": "repo_1", "seconds": 5},
                       {"asset_id": "commons_1", "seconds": 3}]}, approved),
            [{"asset_id": "repo_1", "seconds": 5},
             {"asset_id": "commons_1", "seconds": 3}])
        self.assertIsNone(validate_director_plan(
            {"shots": [{"asset_id": "fake_news", "seconds": 3}]}, approved))
        self.assertEqual(build_fallback_plan(["repo_1"], []),
                         [{"asset_id": "repo_1", "seconds": 12}])

    def test_github_images_only_allow_expected_cdn(self):
        self.assertTrue(approved_github_media_url(
            "https://raw.githubusercontent.com/owner/repo/main/demo.gif"))
        self.assertFalse(approved_github_media_url("https://evil.org/demo.gif"))
        self.assertFalse(approved_github_media_url(
            "https://raw.githubusercontent.com.evil.org/demo.gif"))


if __name__ == "__main__":
    unittest.main()
