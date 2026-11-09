"""Browser mockup demos use genuine README media, keeping exact layout."""
import unittest
from scripts.studio_render import browser_demo_filter


class OfficialReadmeMediaTests(unittest.TestCase):
    def test_demo_overlay_stays_inside_mockup_on_wide_canvas(self):
        value=browser_demo_filter(1920,1080,30)
        self.assertIn("overlay=",value)
        self.assertIn("format=yuv420p",value)
        self.assertIn("pad=",value)
        # Screenshot mockup begins near 53% of the canvas.
        self.assertIn("overlay=1027:",value)

    def test_demo_overlay_supports_portrait_without_paid_renderers(self):
        value=browser_demo_filter(1080,1920,30)
        self.assertIn("overlay=",value)
        self.assertNotIn("http",value)
        self.assertNotIn("api_key",value.lower())

    @unittest.skipUnless(__import__("shutil").which("ffmpeg") and __import__("shutil").which("ffprobe"),"FFmpeg required")
    def test_real_readme_demo_is_embedded_and_keeps_original_frame_count(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from PIL import Image
        import subprocess
        from scripts.studio_render import render_project

        with TemporaryDirectory() as folder:
            base=Path(folder)
            still=base/"official.png"
            Image.new("RGB",(640,360),"#4F7495").save(still)
            demo=base/"official_demo.mp4"
            subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y",
                "-f","lavfi","-i","testsrc=size=320x180:rate=30","-t","2",
                "-c:v","libx264","-pix_fmt","yuv420p",str(demo)],
                check=True,stdout=subprocess.DEVNULL)
            project={
                "schema_version":3,"id":"demo","revision":1,"topic":"Software",
                "script":"Demonstração oficial de aplicativo","fps":30,"aspect":"16:9",
                "total_frames":90,"tracks":[{"id":"video","kind":"video"}],"assets":[],
                "scenes":[{
                    "id":"scene-001","track_id":"video","title":"Chatwoot",
                    "text":"Demonstração oficial de software","kind":"text","asset_id":None,
                    "start_frame":0,"duration_frames":90,"animation":"cut",
                    "framing":"contain","layout":"browser",
                    "repo_url":"https://github.com/chatwoot/chatwoot"
                }]
            }
            with (patch("scripts.repo_stills.capture_repo_stills",return_value=[[str(still)]]),
                  patch("scripts.ai_director.official_repo_image",return_value=str(still)),
                  patch("scripts.ai_director.official_repo_gif",return_value=str(demo))):
                result=render_project(project,base,base/"out",voice="none",
                                      width=320,height=180,capture_github=True)
            self.assertEqual(result["total_frames"],90)
            import json
            credits=json.loads(Path(result["credits"]).read_text(encoding="utf-8"))
            self.assertTrue(any(x.get("type")=="official_readme_demo" for x in credits))


if __name__=="__main__":
    unittest.main()
