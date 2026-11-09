"""Contratos da biblioteca de ganchos para Shorts; sem renderizar vídeos."""
import unittest
from scripts.shorts_hooks import choose_hook, validate_catalog, HookCatalogError

SAMPLE = [
  {"arquivo": "001_queda.mp4", "categoria": "crash", "sha256": "a" * 64, "duracao_segundos": 2.6, "origem": "https://viralhookup.com/hook/queda"},
  {"arquivo": "002_susto.mp4", "categoria": "funny", "sha256": "b" * 64, "duracao_segundos": 1.2, "origem": "https://viralhookup.com/hook/susto"},
  {"arquivo": "003_quase.mp4", "categoria": "crash", "sha256": "c" * 64, "duracao_segundos": 3.0, "origem": "https://viralhookup.com/hook/quase"},
]

class ShortsHooksTest(unittest.TestCase):
    def test_catalog_is_valid_and_has_unique_hashes(self):
        self.assertEqual(len(validate_catalog(SAMPLE)), 3)
        with self.assertRaisesRegex(HookCatalogError,"SHA"):
            validate_catalog(SAMPLE + [dict(SAMPLE[0], arquivo="clone.mp4")])

    def test_does_not_allow_path_traversal_or_unknown_hosts(self):
        with self.assertRaises(HookCatalogError):
            validate_catalog([dict(SAMPLE[0], arquivo="../../secreto.mp4")])
        with self.assertRaises(HookCatalogError):
            validate_catalog([dict(SAMPLE[0], origem="https://evil.example/video")])

    def test_rotates_without_immediate_repeat_by_run_number(self):
        first = choose_hook(SAMPLE, category="crash", seed=1)
        second = choose_hook(SAMPLE, category="crash", seed=2)
        third = choose_hook(SAMPLE, category="crash", seed=3)
        self.assertNotEqual(first["arquivo"], second["arquivo"])
        self.assertEqual(first["arquivo"], third["arquivo"])

    def test_filters_history_and_category(self):
        choice = choose_hook(SAMPLE, category="crash", seed=2, recent=["003_quase.mp4"])
        self.assertEqual(choice["arquivo"],"001_queda.mp4")
        with self.assertRaisesRegex(HookCatalogError,"candidatos"):
            choose_hook(SAMPLE, category="water", seed=1)
    def test_never_selects_invalid_categories(self):
        with self.assertRaises(HookCatalogError):
            choose_hook(SAMPLE, category="not-a-real-category", seed=1)

if __name__ == "__main__":
    unittest.main()
