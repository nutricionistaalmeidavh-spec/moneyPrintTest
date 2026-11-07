"""Google Colab notebook produces the original episode; never paid API."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.frutalandia_colab_notebook import make_notebook

ROOT=Path(__file__).resolve().parents[1]


class ColabEpisodeTests(unittest.TestCase):
    def test_notebook_contains_six_scene_isolation_and_download(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/"original.ipynb"
            make_notebook(out)
            data=json.loads(out.read_text(encoding="utf-8"))
            assert data["nbformat"]==4
            text="\n".join("".join(c["source"]) for c in data["cells"])
            self.assertIn("stories/frutalandia/audio-do-amanha-ep01.json",text)
            self.assertIn("s01",text)
            self.assertIn("s06",text)
            self.assertIn("FRUTALANDIA_RENDER_ENGINE",text)
            self.assertIn("WORKBENCH",text)
            self.assertIn("ffprobe",text)
            self.assertIn("files.download",text)
            self.assertIn("frutalandia-ep01.mp4",text)
            self.assertNotIn("KAGGLE_API_TOKEN",text)
            self.assertNotIn("API_KEY",text)
            self.assertNotIn("pip install -q openai",text)
            self.assertIn("timeout=",text)

    def test_workbench_engine_supported_in_blender(self):
        s=(ROOT/"scripts/frutalandia_blender.py").read_text(encoding="utf-8")
        self.assertIn("FRUTALANDIA_RENDER_ENGINE",s)
        self.assertIn("BLENDER_WORKBENCH",s)

if __name__=="__main__":
    unittest.main()
