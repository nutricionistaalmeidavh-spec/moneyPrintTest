import unittest
from scripts.download_hook_library import parse_slugs, candidates_for, EXCLUDED

class DownloadHooksTests(unittest.TestCase):
    def test_extracts_unique_hook_links(self):
        html = '<a href="/hook/bike-crash"></a><a href="/hook/bike-crash"></a><a href="/hook/lake-fall"></a>'
        self.assertEqual(parse_slugs(html), ["bike-crash", "lake-fall"])

    def test_never_redownloads_existing_ten(self):
        catalogs = {"crash": ["motorcycle-crash", "extra-crash"], "funny": ["bad-drop-in", "funny-dog"]}
        result = candidates_for(catalogs)
        self.assertEqual(result, [("extra-crash", "crash"), ("funny-dog", "funny")])
        self.assertTrue(all(slug not in EXCLUDED for slug, _ in result))

    def test_avoids_duplicate_slug_across_categories(self):
        catalogs = {"crash": ["extra-one"], "funny": ["extra-one", "extra-two"]}
        result = candidates_for(catalogs)
        self.assertEqual(result, [("extra-one", "crash"), ("extra-two", "funny")])

if __name__ == "__main__":
    unittest.main()
