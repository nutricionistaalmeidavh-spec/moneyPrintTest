"""Contracts for a real stylized 3D upgrade and two-second visual QA.

The pipeline may not render 48 seconds until a short preview exists.
"""
import ast
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class VisualV2Tests(unittest.TestCase):
    def test_versioned_materials_characters_and_scenery(self):
        module=ROOT/"scripts/frutalandia_visual_v2.py"
        source=module.read_text(encoding="utf-8")
        ast.parse(source)
        for name in ("enhance_material","detail_character","detail_market","animate_details"):
            self.assertIn("def "+name+"(",source)
        for term in ("ShaderNodeTexNoise","ShaderNodeBump","primitive_bezier_circle_add",
                     "mandacaru","bandeirinha","brilho_olho","pestana"):
            self.assertIn(term,source)

    def test_blender_uses_3d_visuals_and_preview_mode(self):
        src=(ROOT/"scripts/frutalandia_blender.py").read_text(encoding="utf-8")
        for term in ("frutalandia_visual_v2","detail_character(","detail_market(",
                     "FRUTALANDIA_PREVIEW_FRAMES","FRUTALANDIA_PREVIEW","EEVEE",
                     "preview.png","frutalandia-preview.mp4"):
            self.assertIn(term,src)

    def test_production_bundle_includes_visual_module(self):
        src=(ROOT/"scripts/frutalandia_kaggle_bundle.py").read_text(encoding="utf-8")
        self.assertIn('"frutalandia_visual_v2.py"',src)

    def test_qa_workflow_is_short_and_does_not_merge(self):
        src=(ROOT/".github/workflows/frutalandia-visual-preview.yml").read_text(encoding="utf-8")
        self.assertIn("FRUTALANDIA_PREVIEW_FRAMES",src)
        self.assertIn("FRUTALANDIA_RENDER_ENGINE",src)
        self.assertIn("ffprobe",src)
        self.assertIn("upload-artifact",src)
        self.assertNotIn("merge_pull_request",src)
        self.assertNotIn("triggers/produce-frutalandia-cpu.txt",src)
        self.assertNotIn("KAGGLE_API_TOKEN",src)

    def test_existing_characters_have_stable_ids(self):
        for name in ("contador-do-butico-ep01","audio-do-amanha-ep01"):
            story=json.loads((ROOT/f"stories/frutalandia/{name}.json").read_text(encoding="utf-8"))
            self.assertEqual([c["id"] for c in story["characters"]],
                             ["moranguete","uva","mae-pera","pai-caju"])

if __name__=="__main__":
    unittest.main()
