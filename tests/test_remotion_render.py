"""Remotion opt-in adapter contracts; no npm/browser needed for unit tests."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.remotion_render import prepare_manifest, make_render_command, RemotionError


def project():
    return {
        "schema_version": 3, "id": "sample", "revision": 1,
        "topic": "Demo", "script": "Duas cenas", "fps": 30, "aspect": "16:9",
        "total_frames": 90,
        "tracks": [{"id": "video", "kind": "video"}],
        "assets": [],
        "visual_style": "light_motion", "render_engine": "remotion",
        "scenes": [
            {"id": "scene-001", "track_id": "video", "title": "INÍCIO",
             "text": "Primeira cena", "kind": "text", "asset_id": None,
             "start_frame": 0, "duration_frames": 30, "animation": "cut", "layout": "hero"},
            {"id": "scene-002", "track_id": "video", "title": "RESULTADO",
             "text": "Segunda cena", "kind": "text", "asset_id": None,
             "start_frame": 30, "duration_frames": 60, "animation": "slide", "layout": "flow"},
        ],
    }


class RemotionAdapterTests(unittest.TestCase):
    def test_preserves_frame_exact_timeline_without_talkcraft(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = prepare_manifest(project(), Path(folder), Path(folder) / "public")
            self.assertEqual(manifest["totalFrames"], 90)
            self.assertEqual(manifest["fps"], 30)
            self.assertEqual((manifest["width"], manifest["height"]), (1920, 1080))
            self.assertEqual([s["startFrame"] for s in manifest["scenes"]], [0, 30])
            self.assertEqual([s["durationFrames"] for s in manifest["scenes"]], [30, 60])
            self.assertEqual([s["animation"] for s in manifest["scenes"]], ["cut", "slide"])

    def test_approved_media_are_copied_and_paths_are_isolated(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            media = root / "assets" / "approved"
            media.mkdir(parents=True)
            (media / "screenshot.png").write_bytes(b"image")
            video = project()
            video["assets"] = [{"id": "img", "title": "Original", "path": "assets/approved/screenshot.png",
                               "verified": True, "license": "CC BY", "attribution": "Original author"}]
            video["scenes"][1]["asset_id"] = "img"
            manifest = prepare_manifest(video, root, root / "public")
            self.assertEqual(manifest["scenes"][1]["mediaKind"], "image")
            path = manifest["scenes"][1]["media"]
            self.assertTrue(path.startswith("media/"))
            self.assertEqual((root / "public" / path).read_bytes(), b"image")

    def test_missing_media_is_fatal_not_silent_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = project()
            bad["assets"] = [{"id": "img", "title": "Missing", "path": "assets/missing.png",
                              "verified": True, "license": "CC0", "attribution": "Author"}]
            bad["scenes"][1]["asset_id"] = "img"
            with self.assertRaises(RemotionError):
                prepare_manifest(bad, Path(folder), Path(folder) / "public")

    def test_talkcraft_is_separate_noncommercial_adapter(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = project()
            bad["visual_style"] = "talkcraft_edu"
            with self.assertRaises(RemotionError):
                prepare_manifest(bad, Path(folder), Path(folder) / "public")

    def test_cli_is_explicit_and_local_with_no_npx_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            binary = root / "node_modules" / ".bin" / "remotion"
            binary.parent.mkdir(parents=True)
            binary.touch()
            props = root / "props.json"
            props.write_text(json.dumps({"totalFrames": 90}))
            command = make_render_command(root, props, root / "public", root / "out.mp4")
            self.assertEqual(str(binary), command[0])
            self.assertIn("--props", command)
            self.assertIn("--public-dir", command)
            self.assertNotIn("npx", " ".join(command))
            self.assertIn("MoneyPrint", command)

    def test_default_engine_is_open_source_core(self):
        from scripts.studio_render import build_plan
        plain = project()
        plain.pop("render_engine")
        self.assertEqual(build_plan(plain)["total_frames"], 90)


if __name__ == "__main__":
    unittest.main()
