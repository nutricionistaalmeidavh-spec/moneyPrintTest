"""Regression tests: natural-speed motorcycle, clean screen and privacy controls."""
import unittest
from unittest.mock import patch

from scripts.tutorial_editor import (
    RecipeError, hook_timing, validate_hook, validate_recipe, scene
)


class ViralTutorialTests(unittest.TestCase):
    def setUp(self):
        self.recipe = {
            "title":"Como criar um repositório", "format":"9:16",
            "source_resolution":[512,1108], "show_step_labels":False,
            "hook":["COMO CRIAR", "NO GITHUB?"], "outro":["PRONTO"],
            "privacy_masks":[
                {"start":0,"end":10,"x":160,"y":200,"width":300,"height":60}
            ],
            "clips":[{"start":2,"end":4,"speed":1.5}],
            "hook_duration_seconds":3,"opening_style":"universe_gif",
            "universe_seconds":2.3,
            "hook_source_resolution":[512,1108],
            "hook_crop":[16,130,405,720],
            "hook_source_start":0.03,"hook_source_end":0.73,
        }

    def test_hook_is_not_stretched_to_three_seconds(self):
        self.assertEqual(hook_timing(.03,.73,3),(0.7,2.3))
        self.assertEqual(validate_hook(self.recipe,15.43,(512,1108)),(0.7,2.3))

    def test_slow_hook_is_rejected(self):
        with self.assertRaises(RecipeError):
            hook_timing(.03,3.0,3)

    def test_hook_masks_must_match_source_dimensions(self):
        with self.assertRaises(RecipeError):
            validate_hook(self.recipe,15.43,(720,1280))

    def test_clean_recipe_does_not_require_any_caption(self):
        result=validate_recipe(self.recipe,duration=20,resolution=(512,1108))
        self.assertFalse(result["show_step_labels"])

    def test_scene_uses_no_top_or_bottom_text_layers(self):
        # No real ffmpeg invocation needed to check the generated render command.
        with patch("scripts.tutorial_editor.call") as execute:
            scene("recording.mp4",self.recipe["clips"][0],
                  self.recipe["privacy_masks"],"output.mp4")
        cmd=execute.call_args.args[0]
        self.assertEqual(cmd.count("-i"),1)
        self.assertIn("-vf",cmd)
        self.assertNotIn("-filter_complex",cmd)
        self.assertIn("drawbox",cmd[cmd.index("-vf")+1])

    def test_privacy_mask_cannot_cover_only_part_of_take(self):
        self.recipe["privacy_masks"][0]["end"]=3
        with self.assertRaisesRegex(RecipeError,"mascara parcial"):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))


if __name__=="__main__":
    unittest.main()
