import unittest

from scripts.browser_capture import CaptureError, capture_plan, validate_repo_urls, is_github_asset


class BrowserCaptureTests(unittest.TestCase):
    def test_only_public_github_repository_pages_are_accepted(self):
        urls = validate_repo_urls([
            "https://github.com/appwrite/appwrite",
            "https://github.com/payloadcms/payload/",
        ])
        self.assertEqual(urls, [
            "https://github.com/appwrite/appwrite",
            "https://github.com/payloadcms/payload",
        ])

    def test_rejects_unsafe_urls_and_duplicates(self):
        for url in [
            "http://github.com/org/repo", "https://github.com.evil.com/org/repo",
            "https://github.com/org/repo/issues", "https://github.com/org/repo?x=1",
            "https://github.com@localhost/org/repo", "https://github.com/org/../repo",
            "https://github.com/org/repo#readme", "https://github.com/org/repo\n",
            "https://github.com/org", "https://github.com:443/org/repo",
        ]:
            with self.subTest(url=url), self.assertRaises(CaptureError):
                validate_repo_urls([url])
        with self.assertRaises(CaptureError):
            validate_repo_urls(["https://github.com/o/r", "https://github.com/o/r/"])
        with self.assertRaises(CaptureError):
            validate_repo_urls(["https://github.com/o/r"] * 13)

    def test_eight_repositories_for_five_minutes(self):
        urls = [f"https://github.com/org/repo{i}" for i in range(8)]
        plan = capture_plan(urls, 300)
        self.assertEqual(len(plan), 8)
        self.assertEqual([seconds for _, seconds in plan], [38] * 8)

    def test_caps_one_repository_at_sixty_seconds(self):
        self.assertEqual(capture_plan(["https://github.com/o/r"], 300)[0][1], 60)

    def test_only_github_assets_are_loaded(self):
        self.assertTrue(is_github_asset("github.com"))
        self.assertTrue(is_github_asset("github.githubassets.com"))
        self.assertTrue(is_github_asset("avatars.githubusercontent.com"))
        self.assertFalse(is_github_asset("github.com.attacker.example"))
        self.assertFalse(is_github_asset("127.0.0.1"))


if __name__ == "__main__":
    unittest.main()
