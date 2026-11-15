"""Regression tests: 3D mockup scenes are opt-in and require approved local media."""
import unittest
from scripts.studio_render import build_plan, RenderError
from scripts.mockup_3d import validate_mockup


def project(layout="device_mockup_3d", device="laptop", motion="orbit", extension=".mp4"):
    return {
        "schema_version": 3, "fps": 30, "aspect": "9:16", "total_frames": 60,
        "scenes": [{"id": "scene-001", "track_id": "video", "title": "Software",
                    "text": "Teste de tela real.", "kind": "media", "asset_id": "screen",
                    "start_frame": 0, "duration_frames": 60, "layout": layout,
                    "mockup_device": device, "mockup_motion": motion}],
        "assets": [{"id": "screen", "title": "Demonstração", "path": "assets/screen" + extension,
                    "verified": True, "license": "própria", "attribution": "ArtiSys"}]
    }


class MockupContractTest(unittest.TestCase):
    def test_3d_device_scene_compiles(self):
        plan = build_plan(project())
        self.assertEqual(plan["scenes"][0]["layout"], "device_mockup_3d")

    def test_unknown_device_and_motion_rejected(self):
        for key, value in (("mockup_device", "phone"), ("mockup_motion", "infinite-spin")):
            data = project()
            data["scenes"][0][key] = value
            with self.subTest(key=key), self.assertRaises(RenderError):
                build_plan(data)

    def test_3d_requires_approved_screen_media(self):
        data = project(extension=".wav")
        with self.assertRaises(RenderError):
            build_plan(data)
        data = project()
        data["scenes"][0]["asset_id"] = None
        with self.assertRaises(RenderError):
            build_plan(data)

    def test_non_3d_scenes_unchanged(self):
        self.assertEqual(build_plan(project(layout="browser"))["scenes"][0]["layout"], "browser")

    def test_cli_validation(self):
        self.assertEqual(validate_mockup("laptop", "orbit", "9:16"), ("laptop", "orbit", "9:16"))
        for args in (("phone", "orbit", "9:16"), ("laptop", "weird", "9:16"),
                     ("laptop", "orbit", "3:4")):
            with self.assertRaises(ValueError):
                validate_mockup(*args)


if __name__ == "__main__":
    unittest.main()
