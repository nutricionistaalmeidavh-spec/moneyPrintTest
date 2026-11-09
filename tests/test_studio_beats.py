"""Regression coverage for animated reveal beats on the Studio V3 canonical timeline."""
import tempfile
import shutil
from pathlib import Path
import unittest

from scripts.studio_render import _slide, render_project
from PIL import Image, ImageChops


def example():
    return {"schema_version":3,"id":"animated-beats","revision":1,
      "topic":"Uma empresa organizada","script":"Vendas, estoque e financeiro.",
      "fps":30,"aspect":"16:9","total_frames":90,
      "tracks":[{"id":"video","kind":"video"}],"assets":[],
      "scenes":[{"id":"scene-001","track_id":"video","title":"GESTÃO INTEGRADA",
      "text":"Vendas, estoque e financeiro.","kind":"text","asset_id":None,
      "start_frame":0,"duration_frames":90,"animation":"cut","framing":"contain",
      "layout":"flow","eyebrow":"ERPNext","flow_steps":["VENDA","ESTOQUE","FINANCEIRO"]}]}


class MotionBeatsTests(unittest.TestCase):
    def test_progressive_flow_reveal_is_visually_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            p=example()["scenes"][0]
            a,b=Path(d)/"a.png",Path(d)/"b.png"
            _slide(p,a,640,360,None,stage=0)
            _slide(p,b,640,360,None,stage=2)
            with Image.open(a) as i, Image.open(b) as j:
                self.assertIsNotNone(ImageChops.difference(i,j).getbbox())

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_full_render_preserves_frame_count_with_three_beats(self):
        with tempfile.TemporaryDirectory() as d:
            result=render_project(example(),Path(d),Path(d)/"out",voice="none",width=320,height=180)
            self.assertEqual(result["total_frames"],90)
            self.assertGreaterEqual(result["visual_beats"],3)


if __name__=="__main__":
    unittest.main()
