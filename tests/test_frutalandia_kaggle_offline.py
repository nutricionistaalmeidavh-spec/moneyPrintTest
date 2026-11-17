"""Regression: Kaggle offline/DNS failure must never spend 8 minutes on apt."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.frutalandia_episode_runner import ensure_blender
from scripts.frutalandia_kaggle_bundle import make_kernel

ROOT=Path(__file__).resolve().parents[1]
STORY=ROOT/"stories/frutalandia/audio-do-amanha-ep01.json"


class OfflineKaggleGuardsTests(unittest.TestCase):
    def test_kaggle_missing_blender_fails_immediately_without_apt(self):
        with patch("scripts.frutalandia_episode_runner.shutil.which",return_value=None), \
             patch("scripts.frutalandia_episode_runner.run") as execute, \
             patch.dict("os.environ",{"KAGGLE_KERNEL_RUN_TYPE":"Interactive"},clear=False):
            with self.assertRaisesRegex(RuntimeError,"Blender.*ausente|Blender.*indisponível"):
                ensure_blender()
            execute.assert_not_called()

    def test_bundle_checks_gpu_and_blender_before_running_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            program=make_kernel(STORY,ROOT/"scripts/frutalandia_blender.py",
                ROOT/"scripts/frutalandia_episode_runner.py",Path(tmp),"fruitcreator")
            source=program.read_text(encoding="utf-8")
            self.assertIn("nvidia-smi",source)
            self.assertIn("shutil.which('blender')",source)
            self.assertLess(source.index("nvidia-smi"),source.index("subprocess.call("))
            self.assertNotIn("apt-get update",source)
            self.assertIn("FRUTALANDIA_PREFLIGHT",source)

    def test_cpu_fallback_workflow_checks_availability(self):
        src=(ROOT/".github/workflows/frutalandia-cpu-recovery.yml").read_text()
        self.assertIn("workflow_dispatch:",src)
        self.assertIn("ffprobe",src)
        self.assertIn("frutalandia-ep01.mp4",src)
        self.assertIn("upload-artifact",src)
        self.assertIn("blender",src)
        self.assertIn("FRUTALANDIA",src)


if __name__=="__main__":
    unittest.main()
