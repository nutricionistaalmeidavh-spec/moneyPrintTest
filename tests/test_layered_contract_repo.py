"""Repo CI test: layer schema without copying proprietary tutorial videos."""
from pathlib import Path
import json
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]
class LayeredContractRepo(unittest.TestCase):
    def test_blender_3d_storyboard_continuity(self):
        p=json.loads((ROOT/'projects/pdv-artisys-quaternius-v1.json').read_text())
        self.assertEqual(p['total_frames'],2460)
        self.assertEqual(p['character_mode'],'quaternius_standard')
        self.assertEqual(len(p['scenes']),12)
        self.assertFalse(p['use_pil_sprite_fallback'])
        cursor=0
        for scene in p['scenes']:
            self.assertEqual(scene['start_frame'],cursor)
            cursor+=scene['duration_frames']
            self.assertEqual(scene['end_frame'],cursor)
            self.assertEqual(len(scene['editable_tracks']),12)
            for f in scene['assets_referenced']:
                self.assertTrue(f.startswith('assets/') and '..' not in f)
        self.assertEqual(cursor,2460)
    def test_object_screen_and_actor_layers(self):
        p=json.loads((ROOT/'projects/pdv-artisys-quaternius-v1.json').read_text())
        self.assertEqual(sum(len(s['actors']) for s in p['scenes']),23)
        self.assertEqual(sum(len(s['assets_referenced']) for s in p['scenes']),21)
        self.assertTrue(any(a['action']=='deliver_plate' for s in p['scenes'] for a in s['actors']))
        self.assertTrue(all(s['editable_tracks'][5]['name']=='41_REAL_PDV_MOVIE_TEXTURES' for s in p['scenes']))
    def test_source_modules_and_separation(self):
        prefix=ROOT/'scripts/blender_pdv'
        if not prefix.is_dir():prefix=ROOT/'scripts'
        for name in ['rig_acting.py','layered_scene.py','run_layered.py','make_overlays.py']:
            self.assertTrue((prefix/name).is_file())
        q=(prefix/'quaternius_blender.py').read_text()
        self.assertIn('apply_acting',q)
        self.assertIn('import_scene.gltf',q)
        layer=(prefix/'layered_scene.py').read_text()
        self.assertIn('movie_material',layer)
        self.assertIn('render_pass',layer)
    def test_studio_bridge_is_not_claimed_to_be_blender_editor(self):
        p=json.loads((ROOT/'projects/pdv-artisys-studio-v3-bridge.json').read_text())
        self.assertEqual(p['schema_version'],3)
        self.assertEqual(len(p['scenes']),12)
        self.assertIn('does NOT edit bone',p['blender_delivery'])

if __name__=='__main__':unittest.main()
