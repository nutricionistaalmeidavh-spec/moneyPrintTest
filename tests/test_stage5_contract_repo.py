"""Public no-media QA for MoneyPrint PDV Blender scene 05 opt-in.

Does not access private footage or require Blender or commercial services.
"""
from pathlib import Path
import json
import unittest
try:
    from scripts.blender_pdv.build_blender import validate_plan
except ModuleNotFoundError:  # local ZIP keeps scripts/ flat
    from scripts.build_blender import validate_plan

ROOT=Path(__file__).resolve().parents[1]

class Stage5PublicContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project=json.loads((ROOT/'projects/pdv-artisys-quaternius-stage5.json').read_text(encoding='utf8'))

    def test_optin_version_preserves_82_second_timeline(self):
        info=validate_plan(self.project,ROOT,require_media=False)
        self.assertEqual((info['scenes'],info['frames']),(12,2460))
        self.assertEqual(self.project['character_mode'],'quaternius_standard')
        self.assertEqual(self.project['scenes'][4]['duration_frames'],210)

    def test_only_authentic_source_is_allowed(self):
        v=self.project['scenes'][4]['video_texture']
        self.assertEqual(v['file'],'assets/cliente-qr-cena05-clean.mp4')
        self.assertEqual(v['source_original'],'assets/cliente-qr.mp4')
        self.assertEqual(v['editorial_trim_segments_seconds'],[[3,6],[12,16]])
        self.assertTrue(v['no_synthetic_ui'])
        self.assertEqual(v['offset_seconds'],0)

    def test_renderer_does_not_hide_camera_or_light_during_visual_pass(self):
        path=ROOT/'scripts/blender_pdv/layered_scene.py'
        if not path.is_file():path=ROOT/'scripts/layered_scene.py'
        script=path.read_text(encoding='utf8')
        self.assertIn("co.name not in {layer_name, '60_LIGHTS', '70_CAMERA'}",script)
        self.assertIn("if layer_name in ('00_WORLD','60_LIGHTS','70_CAMERA'",script)
        self.assertIn('scene.render.film_transparent=True',script)

    def test_core_r0_does_not_mutate_legacy_request(self):
        self.assertFalse(self.project['autopublish'])
        self.assertTrue(self.project['no_paid_dependencies'])
        self.assertFalse(self.project['use_pil_sprite_fallback'])

if __name__=='__main__':unittest.main()
