"""Kaggle bridge must embed the actual character image and run actual GPU I2V."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.frutalandia_i2v_kaggle_bundle import build_kaggle_kernel

ROOT=Path(__file__).resolve().parents[1]

class KaggleI2VTest(unittest.TestCase):
    def test_script_contains_master_reference_gpu_preflight_and_true_video_generator(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            build_kaggle_kernel(path, "contafrutas", scene_id="s01", slug="frutalandia-i2v-s01")
            script=(path/"run.py").read_text(encoding="utf-8")
            meta=json.loads((path/"kernel-metadata.json").read_text(encoding="utf-8"))
            self.assertGreater(len(script), 140000, "Reference must be embedded, not an external image URL")
            self.assertIn("FRUTALANDIA_I2V_STAGE", script)
            self.assertIn("nvidia-smi", script)
            self.assertIn("FRUTALANDIA_NETWORK_PREFLIGHT", script)
            self.assertIn("preview",script)
            self.assertNotIn("apt-get update", script)
            self.assertNotIn("OPENAI_API_KEY", script)
            self.assertNotIn("KAGGLE_API_TOKEN", script)
            self.assertEqual(meta["id"],"contafrutas/frutalandia-i2v-s01")
            self.assertTrue(meta["enable_gpu"])
            self.assertTrue(meta["enable_internet"])
            self.assertTrue(meta["is_private"])
            self.assertEqual(meta["machine_shape"],"NvidiaTeslaT4")

    def test_scene_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                build_kaggle_kernel(Path(folder),"contafrutas",scene_id="../secret")

if __name__=="__main__":
    unittest.main()
