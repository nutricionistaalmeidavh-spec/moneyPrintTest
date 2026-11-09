import unittest
import tempfile
from pathlib import Path
from PIL import Image

from scripts.animated_slides import make_slide, scene_plan, story_for, STORIES

REPO={"repo_url":"https://github.com/appwrite/appwrite",
      "title":"Appwrite",
      "narration":"O Appwrite oferece serviços para aplicações."}

class MotionSlidesTests(unittest.TestCase):
    def test_eight_projects_have_specific_diagrams(self):
        self.assertEqual(len(STORIES),8)
        for key,(title,steps,summary) in STORIES.items():
            with self.subTest(key=key):
                self.assertEqual(len(steps),3)
                self.assertTrue(title)
                self.assertTrue(summary)
        self.assertEqual(story_for(REPO)[1][1],"Autenticação")

    def test_scenes_prioritize_motion_flow_over_recording(self):
        plan=scene_plan(36,have_pictures=True,first=True)
        kinds=[s[0] for s in plan]
        self.assertEqual(kinds[:5],["intro","benefit","flow","flow","flow"])
        self.assertEqual([s[1] for s in plan if s[0]=="flow"],[0,1,2])
        self.assertAlmostEqual(sum(s[2] for s in plan),36)
        self.assertLess(kinds.count("mockup"),4)

    def test_slide_background_not_white_and_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=[]
            for scene in ("intro","benefit","flow","mockup","use"):
                file=Path(tmp)/f"{scene}.png"
                make_slide(REPO,1,8,scene,file,stage=2,size=(960,540))
                with Image.open(file) as image:
                    self.assertEqual(image.size,(960,540))
                    self.assertTrue(max(image.getpixel((10,10)))<120)
                paths.append(file)
            self.assertEqual(len(paths),5)

    def test_flow_changes_when_each_step_is_revealed(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/"flow0.png"
            b=Path(tmp)/"flow2.png"
            make_slide(REPO,1,8,"flow",a,stage=0,size=(960,540))
            make_slide(REPO,1,8,"flow",b,stage=2,size=(960,540))
            with Image.open(a) as im0,Image.open(b) as im2:
                self.assertNotEqual(im0.tobytes(),im2.tobytes())

if __name__=="__main__":
    unittest.main()
