"""Director V2: golden composition contract before full 5-minute render."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.studio_render import build_plan
from scripts.talkcraft_bridge import prepare_talkcraft_data
from scripts.director_v2 import validate_v2
from scripts.repo_stills import rank_readme_images

ROOT=Path(__file__).resolve().parents[1]

class DirectorV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project=json.loads((ROOT/"projects/5-sistemas-talkcraft-educacional.json").read_text())
        cls.board=json.loads((ROOT/"storyboards/5-sistemas-director-v2.json").read_text())

    def test_v2_paper_palette_and_twenty_five_unique_progressive_compositions(self):
        result=validate_v2(self.board,self.project)
        self.assertEqual(result["frames"],9000)
        self.assertEqual(result["shots"],25)
        self.assertEqual(result["visual_character_count"],5)
        self.assertEqual(self.board["visual_grammar"]["background"],"#F6EEDB")
        self.assertEqual(self.board["render"]["narration"],"piper_pt_BR")
        self.assertEqual(self.board["production_status"],"render_requested")
        self.assertTrue(result["hybrid_scenes"]>=5)

    def test_director_is_actually_passed_to_talkcraft_render_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            manifest=prepare_talkcraft_data(self.project,[],Path(d)/"manifest.json")
        self.assertEqual(manifest["style"],"paper-editorial-v2")
        self.assertEqual(manifest["totalFrames"],9000)
        self.assertTrue(all(scene["direction"]["composition"] for scene in manifest["scenes"]))
        self.assertEqual(len(set(s["direction"]["composition"] for s in manifest["scenes"])),25)
        self.assertEqual(manifest["scenes"][2]["direction"]["effect"],"chaos_thought_cloud")
        self.assertTrue(any(s["direction"]["media_mode"]=="repo_and_interface" for s in manifest["scenes"]))

    def test_repo_screenshot_ranking_prioritises_real_application_previews(self):
        samples=[
          {"alt":"build badge","width":120,"height":22,"src":"https://github.com/actions/badge.svg"},
          {"alt":"Application screenshot of dashboard","width":1400,"height":820,"src":"https://github.com/user-attachments/assets/demo"},
          {"alt":"logo","width":240,"height":240,"src":"https://github.com/user-attachments/assets/logo"}
        ]
        self.assertEqual(rank_readme_images(samples)[0]["alt"],"Application screenshot of dashboard")

    def test_no_faked_app_capture_when_no_readme_screenshot_exists(self):
        samples=[{"alt":"tiny badge","width":80,"height":20,"src":"https://github.com/badge.svg"}]
        self.assertEqual(rank_readme_images(samples),[])

    def test_cannot_duplicate_portrait_identity_in_same_collage(self):
        broken=json.loads(json.dumps(self.board))
        broken["shots"][6]["visual_v2"]["portrait"]="manager_a"
        with self.assertRaisesRegex(ValueError,"portrait"):
            validate_v2(broken,self.project)

    def test_no_diagram_wires_over_text_or_fabricated_screens(self):
        for shot in self.board["shots"]:
            v=shot["visual_v2"]
            self.assertTrue(v["protected_typography"])
            self.assertTrue(v["connectors_avoid_labels"])
            self.assertIn(v["media_mode"],("illustration","repo_and_interface","repo_only"))
            self.assertTrue(v["palette"]=="warm_paper")
            self.assertEqual(v["narration"],shot["narration"])

if __name__=="__main__":unittest.main()
