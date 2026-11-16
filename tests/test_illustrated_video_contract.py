"""Pure (no private media required) illustrated short contract tests for MoneyPrint CI."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import illustrated_video as mod

class IllustratedPDVContract(unittest.TestCase):
    def test_exactly_twelve_contiguous_scenes_and_82_seconds(self):
        self.assertEqual(len(mod.SCENES),12)
        self.assertEqual(sum(mod.DURS),82)
        self.assertEqual(sum(mod.DURS)*mod.FPS,2460)
        self.assertEqual((mod.W,mod.H),(720,1280))

    def test_every_scene_has_contextual_illustrated_action(self):
        for scene in mod.SCENES:
            self.assertTrue(scene['title'])
            self.assertTrue(scene['accent'])
            self.assertTrue(scene['body'])
            self.assertTrue(scene['chars'])
            self.assertTrue(scene['props'])

    def test_real_footage_resolves_only_with_local_assets(self):
        for media in mod.VIDEOS.values():
            self.assertTrue(media.is_relative_to(mod.ROOT))
            self.assertIn('assets/pdv',str(media))
        self.assertFalse(any(str(v).startswith('https://') for v in mod.VIDEOS.values()))

    def test_character_cast_is_consistent(self):
        roles={r for item in mod.SCENES for r in item['chars']}
        self.assertEqual(roles,{'desenvolvedor','garcom','cliente','cozinheiro','caixa','gerente'})

if __name__=='__main__':unittest.main()
