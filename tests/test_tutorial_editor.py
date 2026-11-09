import unittest
from scripts.tutorial_editor import validate_recipe, masks_for_clip, RecipeError

class TutorialPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.recipe = {
            "title": "Tutorial teste", "format": "9:16",
            "source_resolution": [512, 1108],
            "hook": ["GANCHO"], "outro": ["PRONTO"],
            "privacy_masks": [
                {"start": 0, "end": 8, "x": 160, "y": 200,
                 "width": 300, "height": 55}
            ],
            "clips": [{"start": 1, "end": 3,
                       "speed": 1.5, "caption": "PASSO 1"}]
        }

    def test_valid_input_keeps_opaque_redaction(self):
        got = validate_recipe(self.recipe, duration=20, resolution=(512,1108))
        self.assertEqual(len(masks_for_clip(got,got["clips"][0])),1)

    def test_no_privacy_review_is_blocked(self):
        self.recipe["privacy_masks"]=[]
        with self.assertRaisesRegex(RecipeError,"privacy_masks"):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))

    def test_partial_redaction_is_blocked(self):
        self.recipe["privacy_masks"][0]["end"]=2
        with self.assertRaisesRegex(RecipeError,"mascara parcial"):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))

    def test_outside_source_bounds_is_blocked(self):
        self.recipe["privacy_masks"][0]["x"]=500
        with self.assertRaises(RecipeError):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))

    def test_bad_resolution_is_blocked(self):
        with self.assertRaises(RecipeError):
            validate_recipe(self.recipe,duration=20,resolution=(720,1280))

    def test_unrealistic_speed_is_blocked(self):
        self.recipe["clips"][0]["speed"]=99
        with self.assertRaises(RecipeError):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))

    def test_control_characters_are_blocked(self):
        self.recipe["clips"][0]["caption"]="OK\nSEGREDO"
        with self.assertRaises(RecipeError):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))

if __name__=="__main__":
    unittest.main()
