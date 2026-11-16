"""Self-contained checks designed for public GitHub CI (no private footage)."""
import json
import sys
import unittest
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[1]
builder=ROOT/'scripts'/'blender_pdv'/'build_blender.py'
if not builder.is_file(): builder=ROOT/'scripts'/'build_blender.py'
spec=importlib.util.spec_from_file_location('blender_builder',builder)
blender_builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(blender_builder)

class BlenderContractCI(unittest.TestCase):
    def test_schema_and_character_cues_without_private_media(self):
        p=json.loads((ROOT/'projects'/'pdv-artisys-blender-v1.json').read_text(encoding='utf8'))
        self.assertEqual(blender_builder.validate_plan(p,ROOT,require_media=False)['frames'],2460)
        self.assertFalse(p['autopublish'])
        self.assertEqual(len({a['role'] for s in p['scenes'] for a in s['actors']}),6)
        self.assertEqual(sum(bool(s['video_texture']) for s in p['scenes']),11)
    def test_renderer_never_accepts_unsafe_paths(self):
        import copy
        p=json.loads((ROOT/'projects'/'pdv-artisys-blender-v1.json').read_text(encoding='utf8'))
        c=copy.deepcopy(p);c['scenes'][0]['video_texture']['file']='assets/../../secret.mp4'
        with self.assertRaises(ValueError):blender_builder.validate_plan(c,ROOT,require_media=False)

if __name__=='__main__':unittest.main()
