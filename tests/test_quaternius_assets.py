"""Real Quaternius Standard format contract: write failing tests before implementing importer."""
import hashlib
import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
try:
    from scripts.blender_pdv.quaternius_assets import (
        AssetError, inspect_model_gltf, inspect_animation_glb, find_standard_assets,
        install_standard_zip, select_animation, plan_retarget,
    )
except ModuleNotFoundError:
    from scripts.quaternius_assets import (
    AssetError, inspect_model_gltf, inspect_animation_glb, find_standard_assets,
    install_standard_zip, select_animation, plan_retarget,
)


def gltf(armature=('Root','pelvis','spine_01','clavicle_l','upperarm_l','lowerarm_l','hand_l')):
    nodes=[{'name':name} for name in armature]
    return {'asset':{'version':'2.0'},'nodes':nodes,'skins':[{'joints':list(range(len(nodes)))}]}


def glb_fixture(animations=('Idle','Walk','Sitting')):
    nodes=[{'name':n} for n in ('Root','pelvis','spine_01','clavicle_l','upperarm_l','lowerarm_l','hand_l')]
    data={'asset':{'version':'2.0'},'nodes':nodes,'skins':[{'joints':list(range(len(nodes)))}],
          'animations':[{'name':a} for a in animations]}
    blob=json.dumps(data).encode('utf8')
    blob+=b' ' *((4-len(blob)%4)%4)
    return struct.pack('<III',0x46546C67,2,12+8+len(blob))+struct.pack('<II',len(blob),0x4E4F534A)+blob


class QuaterniusAssetsTest(unittest.TestCase):
    def test_inspect_gltf_and_animation_clips(self):
        with tempfile.TemporaryDirectory() as d:
            model=Path(d)/'Regular_Female_FullBody.gltf';model.write_text(json.dumps(gltf()))
            anim=Path(d)/'UAL1_Standard.glb';anim.write_bytes(glb_fixture())
            self.assertIn('hand_l',inspect_model_gltf(model)['bones'])
            self.assertEqual(inspect_animation_glb(anim)['clips'],['Idle','Walk','Sitting'])
            self.assertEqual(select_animation(['Idle','Walk','Sitting'],['Phone_Use','Idle']), 'Idle')

    def test_selection_fails_closed_for_missing_clips(self):
        with self.assertRaises(AssetError):select_animation(['Walk'],['Phone_Use','Idle'])

    def test_import_plan_fails_on_incompatible_bone_rigs(self):
        src={'Root','pelvis','spine_01','clavicle_l','upperarm_l','lowerarm_l','hand_l'}
        self.assertEqual(plan_retarget(src,src)['compatible_bones'],7)
        with self.assertRaises(AssetError):plan_retarget({'pelvis','spine_01'},src)

    def test_rejects_nonstandard_and_unsafe_archive(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            archive=root/'Universal Animation Library[Pro].zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('test.txt','x')
            with self.assertRaises(AssetError):install_standard_zip(archive,root/'out',kind='animations',expected_sha256=None)
            archive=root/'Universal Animation Library[Standard].zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../../private.txt','x')
            with self.assertRaises(AssetError):install_standard_zip(archive,root/'out',kind='animations',expected_sha256=None)
            self.assertFalse((root/'private.txt').exists())

    def test_zip_sha_is_checked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=root/'Universal Animation Library[Standard].zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('Unreal-Godot/UAL1_Standard.glb',glb_fixture())
            with self.assertRaises(AssetError):install_standard_zip(archive,root/'out',kind='animations',expected_sha256='0'*64)
            installed=install_standard_zip(archive,root/'out',kind='animations',expected_sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertEqual(installed.name,'UAL1_Standard.glb')

    def test_local_assets_are_required_no_procedural_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(AssetError):find_standard_assets(Path(d))

    def test_asset_locator_with_fixture_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'models').mkdir();(root/'animations').mkdir()
            (root/'models/Regular_Female_FullBody.gltf').write_text(json.dumps(gltf()))
            (root/'animations/UAL1_Standard.glb').write_bytes(glb_fixture())
            found=find_standard_assets(root)
            self.assertEqual(found['animation'].name,'UAL1_Standard.glb')
            self.assertIn('Female',found['model'].name)

if __name__=='__main__':unittest.main()
