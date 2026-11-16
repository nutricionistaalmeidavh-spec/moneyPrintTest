import copy
import json
import unittest
from pathlib import Path
from scripts.layered_scene import LayerError, validate, _enter, _wrap, _font

PROJECT=Path(__file__).resolve().parents[1]/'projects/pdv-artisys-layered-v1.json'
ROOT=PROJECT.parents[1]

class LayeredSceneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=json.loads(PROJECT.read_text(encoding='utf8'))

    def test_contract_has_12_continuous_scenes_and_82_seconds(self):
        plan=validate(self.spec)
        self.assertEqual(len(plan['scenes']),12)
        self.assertEqual(plan['total_frames'],2460)
        self.assertEqual(sum(s['duration_frames'] for s in plan['scenes']),2460)
        self.assertEqual(plan['fps'],30)
        self.assertTrue(all(len(s['layers'])>=10 for s in plan['scenes']))

    def test_media_paths_are_local_and_never_remote_urls(self):
        paths={layer['path'] for scene in self.spec['scenes'] for layer in scene['layers'] if layer['kind']=='video'}
        self.assertEqual(len(paths),12)
        self.assertTrue(all(path.startswith('assets/pdv/') and path.endswith('.mp4') for path in paths))

    def test_scene_ids_and_layer_ids_unique(self):
        validate(self.spec)
        project=copy.deepcopy(self.spec)
        project['scenes'][1]['id']=project['scenes'][0]['id']
        with self.assertRaises(LayerError):validate(project)
        project=copy.deepcopy(self.spec)
        project['scenes'][0]['layers'][1]['id']=project['scenes'][0]['layers'][0]['id']
        with self.assertRaises(LayerError):validate(project)

    def test_no_path_traversal(self):
        project=copy.deepcopy(self.spec)
        next(l for l in project['scenes'][0]['layers'] if l['kind']=='video')['path']='assets/../secret.mp4'
        with self.assertRaises(LayerError):validate(project)

    def test_no_gaps(self):
        project=copy.deepcopy(self.spec)
        project['scenes'][1]['start_frame']+=1
        with self.assertRaises(LayerError):validate(project)

    def test_progressive_text_reveals_inside_scene(self):
        p={'at':0.5,'enter':'type','enter_seconds':0.9}
        self.assertEqual(_enter(p,.1)[0],0)
        self.assertLess(_enter(p,.7)[3],1)
        self.assertEqual(_enter(p,1.7)[3],1)

    def test_headline_and_accent_do_not_overlap(self):
        for s in self.spec['scenes']:
            layers={l['id']:l for l in s['layers']}
            headline,accent,body=layers['headline'],layers['accent'],layers['body']
            count=len(_wrap(headline['text'],_font(headline['size']),headline['w']-12))
            bottom=headline['y']+count*headline['size']*headline['line_height']
            self.assertGreaterEqual(accent['y'],bottom-3,s['id'])
            count=len(_wrap(accent['text'],_font(accent['size']),accent['w']-12))
            bottom=accent['y']+count*accent['size']*accent['line_height']
            self.assertGreaterEqual(body['y'],bottom-3,s['id'])

if __name__=='__main__': unittest.main()
