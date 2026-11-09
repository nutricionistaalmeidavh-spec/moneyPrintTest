"""Regression: light theme must animate real independent layers and preserve timeline."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.studio_render import build_plan, render_project
from scripts.studio_light_motion import make_layers


def fixture():
    return {
      "schema_version":3,"id":"light-test","revision":1,
      "topic":"Cinco sistemas gratuitos","script":"Os processos podem ficar mais simples.",
      "fps":30,"aspect":"16:9","total_frames":90,"visual_style":"light_motion",
      "tracks":[{"id":"video","kind":"video"}],"assets":[],
      "scenes":[{"id":"scene-001","track_id":"video","title":"GESTÃO INTEGRADA",
        "text":"Os processos podem ficar mais simples.","kind":"text","asset_id":None,
        "start_frame":0,"duration_frames":90,"animation":"cut","framing":"contain",
        "layout":"flow","eyebrow":"ERPNext","flow_steps":["Vendas","Estoque","Financeiro"]}]
    }


class LightMotionTests(unittest.TestCase):
    def test_visual_theme_is_part_of_canonical_render_plan(self):
        self.assertEqual(build_plan(fixture())["visual_style"],"light_motion")

    def test_light_layers_have_clear_background_and_multiple_moving_elements(self):
        with tempfile.TemporaryDirectory() as d:
            bg,layers=make_layers(fixture()["scenes"][0],Path(d),640,360)
            from PIL import Image
            with Image.open(bg) as image:
                r,g,b=image.getpixel((320,160))
                self.assertGreater(min(r,g,b),190)
            self.assertGreaterEqual(len(layers),5)
            self.assertGreater(len({entry[3] for entry in layers}),3)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg required")
    def test_approved_video_moves_inside_light_browser_mockup(self):
        from scripts.studio_light_motion import render_light_scene
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            video=root/"demo.mp4"
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                "-f","lavfi","-i","testsrc2=s=160x90:r=15","-t","2",
                "-pix_fmt","yuv420p",str(video)],check=True)
            scene={**fixture()["scenes"][0],"layout":"browser"}
            result=render_light_scene(scene,root/"out.mp4",root,1,30,75,640,360,
                                     moving_preview=video)
            self.assertTrue(result["embedded_video"])
            self.assertEqual(result["duration"],2.5)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg required")
    def test_real_mp4_contains_motion_between_frames_not_just_cuts(self):
        with tempfile.TemporaryDirectory() as d:
            from PIL import Image,ImageChops
            output=render_project(fixture(),Path(d),Path(d)/"out",
                                  voice="none",width=640,height=360)
            self.assertEqual(output["total_frames"],90)
            self.assertEqual(output["visual_style"],"light_motion")
            path=output["output"]
            shots=[]
            for moment in (0.2,1.3,2.6):
                image=Path(d)/f"frame-{moment}.png"
                subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                                "-ss",str(moment),"-i",str(path),
                                "-frames:v","1",str(image)],check=True)
                shots.append(Image.open(image).convert("RGB"))
            self.assertIsNotNone(ImageChops.difference(shots[0],shots[1]).getbbox())
            self.assertIsNotNone(ImageChops.difference(shots[1],shots[2]).getbbox())


if __name__=="__main__":
    unittest.main()
