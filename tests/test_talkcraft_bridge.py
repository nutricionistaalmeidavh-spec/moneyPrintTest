"""Contract: original Talkcraft imports, not hand-made Pillow substitutes."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.studio_render import build_plan
from scripts.talkcraft_bridge import (
    UPSTREAM_SHA, clip_aligned_cues, prepare_talkcraft_data, select_recipe
)

def example():
    return {"schema_version":3,"id":"edu-video","revision":1,
      "topic":"Repositorios gratuitos","script":"O caos da planilha. Use um CRM.",
      "fps":30,"aspect":"16:9","total_frames":180,"visual_style":"talkcraft_edu",
      "tracks":[{"id":"video","kind":"video"}],"assets":[],
      "scenes":[
        {"id":"scene-001","track_id":"video","title":"O CAOS DA PLANILHA",
         "text":"O caos da planilha.","kind":"text","asset_id":None,
         "start_frame":0,"duration_frames":90,"animation":"cut","framing":"contain","layout":"flow"},
        {"id":"scene-002","track_id":"video","title":"CRM",
         "text":"Use um CRM.","kind":"text","asset_id":None,
         "start_frame":90,"duration_frames":90,"animation":"cut","framing":"contain","layout":"browser"}]}

class TalkcraftBridgeTests(unittest.TestCase):
    def test_opt_in_style_keeps_existing_modes(self):
        self.assertEqual(build_plan(example())["visual_style"],"talkcraft_edu")
        old=example();old["visual_style"]="light_motion"
        self.assertEqual(build_plan(old)["visual_style"],"light_motion")
        self.assertRegex(UPSTREAM_SHA,r"^[0-9a-f]{40}$")

    def test_phrase_matches_are_relative_to_measured_words(self):
        words=[{"word":"o","start":0.04,"end":0.2},
               {"word":"caos","start":0.53,"end":0.91},
               {"word":"da","start":0.93,"end":1.08},
               {"word":"planilha","start":1.1,"end":1.55},
               {"word":"crm","start":3.62,"end":3.92}]
        cues=clip_aligned_cues(example(),words)
        self.assertEqual([c["effect"] for c in cues],["scribble_chaos","crm_orbit"])
        self.assertAlmostEqual(cues[0]["at"],0.53)
        self.assertAlmostEqual(cues[1]["at"],3.62)
        self.assertEqual(cues[0]["method"],"measured_whisper_pt")

    def test_no_fabricated_word_time_when_not_aligned(self):
        self.assertEqual(clip_aligned_cues(example(),[]),[])

    def test_original_recipe_mapping_and_style_light(self):
        self.assertEqual(select_recipe("crm"),"orbit-drift")
        self.assertEqual(select_recipe("atendimento"),"chat-message-flow")
        self.assertEqual(select_recipe("vendas"),"numbered-step-stack")
        self.assertEqual(select_recipe("caos"),"pencil-draw")

    def test_project_manifest_exact_frames_and_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/"project.json"
            data=prepare_talkcraft_data(example(),[],output)
            self.assertTrue(output.is_file())
            self.assertEqual(data["totalFrames"],180)
            self.assertEqual(data["style"],"pastel-light")
            self.assertEqual(len(data["scenes"]),2)
            self.assertIn("Vincentwei1021/video-talkcraft",data["upstream"])
            self.assertTrue(data["license_notice"])
            self.assertEqual(json.loads(output.read_text())["totalFrames"],180)

if __name__=="__main__":unittest.main()
