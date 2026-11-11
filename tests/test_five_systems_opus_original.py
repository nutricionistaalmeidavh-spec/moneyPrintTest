"""Guarantee the full film uses upstream Opus motions, never Python recreations."""
import json
import unittest
from collections import Counter
from pathlib import Path
from scripts.prepare_five_systems_opus import validate_board, PROJECT, BOARD, REQUIRED_MEDIA, MOTION_SOURCES
ROOT=Path(__file__).resolve().parents[1]

class OpusOriginalFullTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project=json.loads((ROOT/PROJECT).read_text(encoding="utf-8"))
        cls.board=json.loads((ROOT/BOARD).read_text(encoding="utf-8"))

    def test_25_original_motions_cover_9000_frames(self):
        summary=validate_board(self.board,self.project)
        self.assertEqual(summary["frames"],9000)
        self.assertEqual(summary["scenes"],25)
        self.assertGreaterEqual(summary["distinct_motions"],20)
        self.assertLessEqual(summary["max_repetition"],2)

    def test_every_scene_keeps_its_canonical_narration(self):
        for src,shot in zip(self.project["scenes"],self.board["scenes"]):
            self.assertEqual(src["text"],shot["say"])
            self.assertEqual(src["duration_frames"],shot["min"])
            self.assertFalse(shot.get("layers"))
            self.assertEqual(shot["transition"]["type"],"cut")

    def test_all_proof_scenes_use_genuine_image_paths(self):
        self.assertEqual(len(REQUIRED_MEDIA),5)
        for scene_index,software in REQUIRED_MEDIA.items():
            shot=self.board["scenes"][scene_index-1]
            used=str(shot["props"])
            self.assertIn("software/"+software+"/verified.png",used)
            self.assertIn("software/"+software+"/verified.png",str(shot["props"]))
        self.assertTrue(all(url.startswith("https://github.com/") for url in MOTION_SOURCES.values()))

    def test_render_path_is_direct_original_cli_not_adapted_python(self):
        runner=(ROOT/".github/workflows/five-systems-opus-original.yml").read_text()
        self.assertIn("node cli/direct.mjs",runner)
        self.assertIn("git clone",runner)
        self.assertIn("v1.2.0",runner)
        self.assertNotIn("python -m scripts.full300_editor",runner)
        self.assertNotIn("python -m scripts.opus_motion_adapter",runner)
        self.assertIn("Piper",runner)
        self.assertIn("upload-artifact",runner)

    def test_all_22_original_motion_sources_are_checked_into_repository(self):
        paths=[
            "text/stamp-slam","camera/board-camera",
            "ui/ui-accumulation-storm","image/ken-burns",
            "data/flow-diagram","text/myth-vs-fact",
            "ui/notification-stack","document/document-zoom-highlight",
            "data/deploy-pipeline-stages","text/flashcard-flip-deck",
            "data/network-graph","ui/device-mockup",
            "ui/chat-bubbles","ui/glass-lesson-card",
            "ui/card-stack-cascade","fx/magnifier-loupe",
            "data/gantt-timeline","hud/radial-blueprint",
            "data/step-process-numbered","text/counting-objects",
            "product/spec-compare-table","text/end-screen-cards"]
        self.assertEqual(len(paths),22)
        for name in paths:
            source=ROOT/"vendor/opus-motion/src/motions"/(name+".tsx")
            self.assertTrue(source.is_file(),str(source))
            self.assertIn("defineMotion",source.read_text(encoding="utf-8"),str(source))
        self.assertTrue((ROOT/"vendor/opus-motion/LICENSE").is_file())

    def test_official_twenty_screenshot_fallback_when_github_capture_fails(self):
        import tempfile
        from unittest.mock import patch
        from PIL import Image
        from scripts.prepare_five_systems_opus import _capture_repos, OFFICIAL_APP_DOCS

        self.assertEqual(OFFICIAL_APP_DOCS["twenty"],"https://twenty.com")
        def github_capture(urls,out):
            if "twentyhq" in urls[0]:
                raise RuntimeError("GitHub temporarily unavailable")
            folder=out/"repo_01"
            folder.mkdir(parents=True,exist_ok=True)
            p=folder/"top.png"
            Image.new("RGB",(1440,900),"#243D5A").save(p)
            return [[str(p)]]
        def official_doc(tool,path):
            path.parent.mkdir(parents=True,exist_ok=True)
            Image.effect_noise((1200,700),64).convert("RGB").save(path)
            return {"type":"official_documentation_real_image",
                    "url":"https://twenty.com","image_source":"verified-image",
                    "description":"CRM UI"}
        with tempfile.TemporaryDirectory() as temp:
            with patch("scripts.repo_stills.capture_repo_stills",side_effect=github_capture):
                with patch("scripts.prepare_five_systems_opus._capture_official_doc",
                           side_effect=official_doc):
                    result=_capture_repos(Path(temp))
            self.assertIn("twenty",result)
            self.assertEqual(result["twenty"]["type"],"official_documentation_real_image")
            self.assertTrue((Path(temp)/"public/software/twenty/verified.png").is_file())

    def test_twenty_rejects_small_external_image_and_uses_vendored_real_readme(self):
        import tempfile
        from unittest.mock import patch
        from PIL import Image
        from scripts.prepare_five_systems_opus import _capture_repos

        def fake_repo_capture(urls,out):
            folder=out/"repo_01"
            folder.mkdir(parents=True,exist_ok=True)
            p=folder/"top.png"
            Image.new("RGB",(1440,900),"#243D5A").save(p)
            return [[str(p)]]

        def too_small_official(tool,path):
            path.parent.mkdir(parents=True,exist_ok=True)
            if tool=="twenty":
                # Over 8000 bytes, but not a legible application screenshot.
                Image.effect_noise((540,260),72).convert("RGB").save(path)
            else:
                Image.effect_noise((1200,700),72).convert("RGB").save(path)
            return {"type":"official_documentation_real_image",
                    "url":"https://twenty.com","image_source":"test invalid crop"}

        with tempfile.TemporaryDirectory() as temp:
            with patch("scripts.repo_stills.capture_repo_stills",side_effect=fake_repo_capture), \
                 patch("scripts.prepare_five_systems_opus._capture_official_doc",
                       side_effect=too_small_official):
                results=_capture_repos(Path(temp))
            twenty=Path(temp)/"public/software/twenty/verified.png"
            self.assertEqual(results["twenty"]["type"],"github_official_readme_asset_local")
            with Image.open(twenty) as image:
                self.assertEqual(image.size,(1600,1000))

    def test_direct_twenty_asset_is_genuine_image_only(self):
        import tempfile
        from PIL import Image
        from scripts.prepare_five_systems_opus import (
            _capture_twenty_readme_asset, TWENTY_OFFICIAL_README_IMAGE,
        )
        self.assertTrue(TWENTY_OFFICIAL_README_IMAGE.startswith(
            "https://raw.githubusercontent.com/twentyhq/twenty/"))
        source=ROOT/"assets/original_sources/twenty_crm_readme.webp.b64"
        self.assertTrue(source.is_file())
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/"verified.png"
            meta=_capture_twenty_readme_asset(out)
            self.assertEqual(meta["type"],"github_official_readme_asset_local")
            with Image.open(out) as authentic:
                self.assertEqual(authentic.size,(1600,1000))
            self.assertEqual(len(meta["source_sha256"]),64)
            self.assertEqual(meta["source_file"],"assets/original_sources/twenty_crm_readme.webp.b64")

    def test_screen_labels_do_not_expose_capture_metadata(self):
        for scene in self.board["scenes"]:
            strings=str(scene["props"]).lower()
            for forbidden in ("captura real", "screenshot do readme", "tela fictícia", "falso dashboard", "mockup fictício"):
                self.assertNotIn(forbidden,strings)

if __name__=="__main__":unittest.main()
