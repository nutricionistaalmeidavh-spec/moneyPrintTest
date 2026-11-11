"""Pilot24 regression tests: two canonical scenes, 8 distinct cuts, no fake UI."""
import unittest
from PIL import Image, ImageChops
from scripts.pilot24_editor import BEATS, FPS, DURATION, ANCHORS, CAPTURE_URL, validate_plan, frame_at

class Pilot24Tests(unittest.TestCase):
    def test_eight_visual_beats_fill_exactly_24_seconds(self):
        self.assertTrue(validate_plan())
        self.assertEqual((FPS,DURATION,len(BEATS)),(30,24,8))
        self.assertEqual(BEATS[0][0],0)
        self.assertEqual(BEATS[-1][1],24)
        self.assertTrue(all(a[1]==b[0] for a,b in zip(BEATS,BEATS[1:])))
        self.assertTrue(all(b-a<4 for a,b,_ in BEATS))

    def test_real_captures_and_measured_alignment_provenance(self):
        self.assertEqual(CAPTURE_URL,"https://github.com/frappe/erpnext")
        self.assertTrue(all(c["method"] in ("measured_whisper_pt","interpolated_between_measured_pt") for c in ANCHORS))
        self.assertAlmostEqual(ANCHORS[1]["at"],15.66)

    def test_all_beats_draw_nonempty_frames_in_lowres(self):
        repo=Image.new("RGB",(1440,900),(24,30,41))
        app=Image.new("RGB",(838,534),(245,245,245))
        colors=[]
        for start,end,name in BEATS:
            image=frame_at((start+end)/2,repo,app,640,360)
            self.assertEqual(image.size,(640,360),name)
            blank=Image.new("RGB",(640,360),(246,238,219))
            self.assertIsNotNone(ImageChops.difference(image,blank).getbbox(),name)
            colors.append(image.getpixel((30,30)))
        self.assertIn((24,30,41),colors)

    def test_visual_beats_have_explicit_media_proof_vs_diagram(self):
        self.assertEqual([x[2] for x in BEATS][4:6],["github","interface"])
        self.assertEqual(BEATS[7][2],"implantacao")

if __name__=="__main__":unittest.main()
