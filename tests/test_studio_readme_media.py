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


if __name__=="__main__":
    unittest.main()
