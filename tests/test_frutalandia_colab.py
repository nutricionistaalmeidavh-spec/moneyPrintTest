"""Contract tests for runnable, safe Google Colab notebooks for both episodes."""
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NOTEBOOKS={
    "butico": ("notebooks/frutalandia-contador-do-butico-colab.ipynb",
               "stories/frutalandia/contador-do-butico-ep01.json",
               "frutalandia-contador-ep01.mp4"),
    "audio": ("notebooks/frutalandia-audio-do-amanha-colab.ipynb",
              "stories/frutalandia/audio-do-amanha-ep01.json",
              "frutalandia-audio-do-amanha-ep01.mp4"),
}


class ColabNotebookTests(unittest.TestCase):
    def test_complete_six_scene_episodes_and_download(self):
        for key,(path,story,final) in NOTEBOOKS.items():
            with self.subTest(episode=key):
                notebook=json.loads((ROOT/path).read_text(encoding="utf-8"))
                self.assertEqual(notebook["nbformat"],4)
                self.assertEqual(notebook["metadata"]["kernelspec"]["language"],"python")
                self.assertGreaterEqual(len(notebook["cells"]),7)
                code="".join("".join(cell["source"]) for cell in notebook["cells"]
                             if cell["cell_type"]=="code")
                self.assertIn(story,code)
                for token in (
                    "s01","s02","s03","s04","s05","s06",
                    "FRUTALANDIA_RENDER_ENGINE","WORKBENCH",
                    "ffprobe","probe_mp4","files.download","piper-tts==1.8.0",
                    "xvfb-run","timeout=","BAIXAR_AUTOMATICAMENTE",
                    "LIBGL_ALWAYS_SOFTWARE","--scene-id"
                ):
                    self.assertIn(token,code)
                self.assertIn(final,code)
                self.assertNotIn("KAGGLE_API_TOKEN",code)
                self.assertNotIn("OPENAI_API_KEY",code)
                self.assertNotIn("api_key=",code.lower())
                for i,cell in enumerate(notebook["cells"]):
                    if cell["cell_type"]=="code":
                        compile("".join(cell["source"]),f"{key}/cell-{i}","exec")

    def test_original_storyboards_six_scenes_48_seconds(self):
        for key,(_,path,_) in NOTEBOOKS.items():
            story=json.loads((ROOT/path).read_text(encoding="utf-8"))
            with self.subTest(episode=key):
                self.assertEqual(len(story["scenes"]),6)
                self.assertEqual(sum(c["seconds"] for c in story["scenes"]),48)
                self.assertEqual(story["format"]["aspect"],"9:16")
                self.assertFalse(story["policies"]["auto_publish"])
                self.assertFalse(story["policies"]["paid_providers"])

    def test_renderer_supports_stable_workbench_and_correct_path(self):
        blender=(ROOT/"scripts/frutalandia_blender.py").read_text(encoding="utf-8")
        runner=(ROOT/"scripts/frutalandia_episode_runner.py").read_text(encoding="utf-8")
        self.assertIn("FRUTALANDIA_RENDER_ENGINE",blender)
        self.assertIn("BLENDER_WORKBENCH",blender)
        self.assertIn('with_name("frutalandia_blender.py")',runner)
        self.assertIn('FRUTALANDIA_SCENE_ID',runner)

if __name__=="__main__":
    unittest.main()
