"""Regression for a renderer that remained stuck inside a compound apt/pip/browser step."""
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/five-systems-opus-original.yml"

class FiveSystemsOpusBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow=WORKFLOW.read_text(encoding="utf-8")

    def test_independent_setup_steps_prevent_unattributed_install_hang(self):
        for label in ("Verificar FFmpeg e fontes", "Instalar dependências Python com limite",
                      "Instalar Chromium headless com limite", "Testar Chromium headless"):
            self.assertIn("name: "+label, self.workflow)
        self.assertNotIn("Instalar FFmpeg, Piper e navegador (sem API paga)",self.workflow)

    def test_ffmpeg_does_not_use_unreachable_apt_mirrors(self):
        self.assertNotIn("apt-get update",self.workflow)
        self.assertNotIn("apt-get install",self.workflow)
        self.assertIn("autobuild-2026-11-06-12-50",self.workflow)
        self.assertIn("ffmpeg-N-128532-g5d85b7bfb2-linux64-gpl",self.workflow)
        self.assertIn('"$VERSION.tar.xz"',self.workflow)
        self.assertIn("checksums.sha256",self.workflow)
        self.assertIn("sha256sum -c",self.workflow)
        self.assertIn("libx264",self.workflow)

    def test_no_expensive_full_browser_or_unlimited_package_install(self):
        self.assertNotIn("playwright install --with-deps chromium",self.workflow)
        self.assertIn("playwright install chromium --only-shell",self.workflow)
        self.assertIn("timeout 240s",self.workflow)
        self.assertIn("timeout 360s",self.workflow)

    def test_old_stuck_run_replaced_and_heartbeat_can_attribute_failure(self):
        self.assertIn("cancel-in-progress: true",self.workflow)
        self.assertIn("PIP_DEFAULT_TIMEOUT",self.workflow)
        self.assertIn("playwright.sync_api",self.workflow)

    def test_original_opus_motor_preserved(self):
        self.assertIn("node cli/direct.mjs",self.workflow)
        self.assertIn("v1.2.0",self.workflow)
        self.assertNotIn("scripts.opus_motion_adapter",self.workflow)
        self.assertIn("upload-artifact",self.workflow)

if __name__=="__main__":unittest.main()
