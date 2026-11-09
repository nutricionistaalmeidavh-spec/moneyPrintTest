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

    def test_document_overload_is_distinct_from_scribble_and_document_organization(self):
        p = example()
        p["scenes"][0]["text"]="Os contratos, notas e anexos ficam espalhados."
        p["scenes"][1]["text"]="O Paperless organiza documentos por busca."
        words = [{"word":"contratos","start":0.51,"end":1.09},
                 {"word":"papéis","start":0.7,"end":1.15},
                 {"word":"paperless","start":3.22,"end":3.7}]
        cues = clip_aligned_cues(p,words)
        self.assertEqual([c["effect"] for c in cues],
                         ["paper_overload","document_flow"])
        self.assertEqual(cues[0]["recipe"],"stack-fan-out")
        self.assertEqual(cues[1]["recipe"],"numbered-step-stack")

    def test_essential_effects_for_five_systems_can_be_audited(self):
        from scripts.talkcraft_bridge import audit_illustrations
        p=example()
        p["scenes"][0]["text"]="O caos da planilha."
        p["scenes"][1]["text"]="Um CRM organiza clientes."
        cues=clip_aligned_cues(p,[
            {"word":"caos","start":0.4,"end":0.8},
            {"word":"CRM","start":3.7,"end":4.0}])
        report=audit_illustrations(p,cues)
        self.assertEqual(report["required"],["scribble_chaos","crm_orbit"])
        self.assertEqual(report["missing"],[])
        self.assertEqual(audit_illustrations(p,[])["missing"],
                         ["scribble_chaos","crm_orbit"])

    def test_render_assets_for_native_paper_fan(self):
        from scripts.talkcraft_render import write_document_assets
        with tempfile.TemporaryDirectory() as d:
            write_document_assets(Path(d))
            pages=[Path(d)/f"paper_{i}.svg" for i in range(1,6)]
            self.assertTrue(all(page.is_file() for page in pages))
            self.assertTrue(all('xmlns="http://www.w3.org/2000/svg"' in page.read_text()
                                for page in pages))
            self.assertIn("CONTRATO",pages[0].read_text())

    def test_missing_planilha_asr_uses_measured_neighbouring_words_not_fake_exact_time(self):
        p=example()
        p["scenes"][0]["text"]="A empresa controla estoque numa planilha, vendas em outra."
        words=[{"word":"estoque","start":0.6,"end":0.9},
               {"word":"vendas","start":1.9,"end":2.3}]
        cues=clip_aligned_cues(p,words)
        scribbles=[c for c in cues if c["effect"]=="scribble_chaos"]
        self.assertEqual(len(scribbles),1)
        self.assertEqual(scribbles[0]["method"],"interpolated_between_measured_pt")
        self.assertGreater(scribbles[0]["at"],0.9)
        self.assertLess(scribbles[0]["at"],1.9)

    def test_direct_keyword_timing_keeps_true_measured_timestamp(self):
        p=example()
        p["scenes"][0]["text"]="O caos da planilha atrapalha."
        words=[{"word":"caos","start":0.55,"end":0.9},
               {"word":"planilha","start":1.2,"end":1.5}]
        cues=clip_aligned_cues(p,words)
        ca=[c for c in cues if c["effect"]=="scribble_chaos"]
        self.assertEqual(len(ca),1)
        self.assertAlmostEqual(ca[0]["at"],0.55)
        self.assertEqual(ca[0]["method"],"measured_whisper_pt")

    def test_no_fabricated_word_time_when_not_aligned(self):
        self.assertEqual(clip_aligned_cues(example(),[]),[])

    def test_original_recipe_mapping_and_style_light(self):
        self.assertEqual(select_recipe("crm"),"orbit-drift")
        self.assertEqual(select_recipe("atendimento"),"chat-message-flow")
        self.assertEqual(select_recipe("vendas"),"numbered-step-stack")
        self.assertEqual(select_recipe("caos"),"pencil-draw")
        self.assertEqual(select_recipe("contratos"),"stack-fan-out")

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
