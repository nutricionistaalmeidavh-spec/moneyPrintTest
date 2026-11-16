import importlib.util
import json
import subprocess
import sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
BUILDER=ROOT/'scripts'/'blender_pdv'/'build_blender.py'
if not BUILDER.is_file():BUILDER=ROOT/'scripts'/'build_blender.py'
spec=importlib.util.spec_from_file_location('builder',BUILDER)
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)

class QuaterniusPilotTest(unittest.TestCase):
 def test_pilot_character_mode_is_opt_in_not_legacy_mutation(self):
  legacy=json.loads((ROOT/'projects'/'pdv-artisys-blender-v1.json').read_text())
  actual=json.loads((ROOT/'projects'/'pdv-artisys-quaternius-v1.json').read_text())
  self.assertEqual(legacy['character_mode'],'procedural_preview')
  self.assertEqual(actual['character_mode'],'quaternius_standard')
  self.assertEqual(actual['scenes'][4]['video_texture']['file'],'assets/cliente-qr.mp4')
  self.assertEqual(actual['scenes'][4]['actors'][0]['action'],'phone_tap')
  self.assertEqual(builder.validate_plan(actual,ROOT,require_media=False)['frames'],2460)
 def test_contract_only_checks_without_paid_models(self):
  p=subprocess.run([sys.executable,str(BUILDER),
       '--project',str(ROOT/'projects'/'pdv-artisys-quaternius-v1.json'),
       '--scene','05','--dry-run','--contract-only'],text=True,capture_output=True,check=True)
  data=json.loads(p.stdout)
  self.assertEqual(data['selected'],['05']);self.assertEqual(data['character_mode'],'quaternius_standard')
 def test_real_assets_required_before_render(self):
  p=subprocess.run([sys.executable,str(BUILDER),
       '--project',str(ROOT/'projects'/'pdv-artisys-quaternius-v1.json'),
       '--scene','05','--dry-run'],text=True,capture_output=True)
  self.assertNotEqual(p.returncode,0)
  self.assertTrue('Standard' in p.stderr or 'Missing video' in p.stderr)
 def test_animation_is_not_png_swap(self):
  file=BUILDER.parent/'quaternius_blender.py'
  code=file.read_text(encoding='utf8')
  for token in ('bpy.ops.import_scene.gltf','source.animation_data.action=selected',
                'Quaternius UAL Standard','phone_tap','quaternius_source'):
   self.assertIn(token,code)

if __name__=='__main__':unittest.main()
