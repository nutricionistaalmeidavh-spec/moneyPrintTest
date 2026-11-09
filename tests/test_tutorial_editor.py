"""MoneyPrint tutorial: fail-closed privacy and editing contracts."""
import unittest
from scripts.tutorial_editor import validate_recipe, masks_for_clip, RecipeError

class TutorialEditorTests(unittest.TestCase):
    def setUp(self):
        self.recipe={
            "title":"Exemplo","format":"9:16","source_resolution":[512,1108],
            "hook":["INICIO"],"outro":["FIM"],
            "privacy_masks":[{"start":0,"end":8,"x":140,"y":100,"width":240,"height":60}],
            "clips":[{"start":1,"end":3,"speed":1.5}]
        }
    def test_good_recipe(self):
        r=validate_recipe(self.recipe,duration=20,resolution=(512,1108))
        self.assertEqual(len(masks_for_clip(r,r["clips"][0])),1)
    def test_private_clip_with_partial_mask_is_rejected(self):
        self.recipe["privacy_masks"][0]["end"]=2
        with self.assertRaisesRegex(RecipeError,"parcial"):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))
    def test_missing_privacy_review_is_rejected(self):
        self.recipe["privacy_masks"]=[]
        with self.assertRaisesRegex(RecipeError,"privacy_masks"):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))
    def test_mask_out_of_bounds_is_rejected(self):
        self.recipe["privacy_masks"][0]["x"]=500
        with self.assertRaises(RecipeError):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))
    def test_wrong_source_resolution_is_rejected(self):
        with self.assertRaises(RecipeError):
            validate_recipe(self.recipe,duration=20,resolution=(400,900))
    def test_invalid_speed_or_caption_is_rejected(self):
        self.recipe["clips"][0]["speed"]=100
        with self.assertRaises(RecipeError):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))
        self.recipe["clips"][0]["speed"]=1.5
        self.recipe["clips"][0]["caption"]="x\nBAD"
        with self.assertRaises(RecipeError):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))
    def test_source_duration_is_enforced(self):
        self.recipe["clips"][0]["end"]=21
        with self.assertRaises(RecipeError):
            validate_recipe(self.recipe,duration=20,resolution=(512,1108))


class CleanPresentationTests(unittest.TestCase):
    def test_fast_original_hook_not_slowed(self):
        from scripts.tutorial_editor import hook_timing
        hook,universe=hook_timing(0.03,0.83)
        self.assertAlmostEqual(hook,0.8)
        self.assertAlmostEqual(universe,2.2)
        with self.assertRaises(RecipeError):
            hook_timing(0,3.5)
    def test_no_overlaid_caption_or_step_number_in_recipe(self):
        request={"title":"x","format":"9:16","source_resolution":[512,1108],
                 "hook":["INTRO"],"outro":["FIM"],
                 "privacy_masks":[{"start":0,"end":8,"x":140,"y":100,"width":240,"height":60}],
                 "clips":[{"start":1,"end":3,"speed":1.5}]}
        validate_recipe(request,duration=20,resolution=(512,1108))
        request["clips"][0]["caption"]="NÃO MOSTRAR"
        with self.assertRaises(RecipeError):
            validate_recipe(request,duration=20,resolution=(512,1108))

if __name__=="__main__":
    unittest.main()
