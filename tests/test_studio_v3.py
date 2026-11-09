"""P0–P1 contracts: canonical timeline, safe assets and reference diagnostics."""
import unittest
from scripts.studio_project import (
    StudioProjectError, create_project, validate_project,
    update_scene, rank_assets, to_render_request
)
from scripts.reference_analyzer import parse_cuts, describe_rhythm, plan_reference


class CanonicalStudioTests(unittest.TestCase):
    def make_project(self, **extra):
        args = {"topic": "PDV em restaurante", "script": "Receba clientes no caixa. Registre pedidos e organize o atendimento. Veja os relatórios.", "duration_seconds": 30, "fps": 30, "aspect": "9:16"}
        args.update(extra)
        return create_project(**args)

    def test_storyboard_fits_duration_without_rounded_gaps(self):
        project = self.make_project()
        self.assertEqual(project["schema_version"], 3)
        self.assertEqual(project["total_frames"], 900)
        self.assertGreaterEqual(len(project["scenes"]), 3)
        cursor = 0
        for scene in project["scenes"]:
            self.assertEqual(scene["start_frame"], cursor)
            self.assertGreater(scene["duration_frames"], 0)
            cursor += scene["duration_frames"]
        self.assertEqual(cursor, 900)
        self.assertEqual(validate_project(project)["total_frames"], 900)

    def test_selection_only_uses_approved_licensed_assets(self):
        assets = [
            {"id": "a", "title": "Atendimento em restaurante", "tags": ["caixa", "cliente", "restaurante"], "license": "CC0", "attribution": "Autor", "verified": True, "path": "assets/restaurante.mp4"},
            {"id": "b", "title": "Caixa de restaurante", "tags": ["caixa", "restaurante"], "license": "", "attribution": "", "verified": True, "path": "assets/outro.mp4"},
            {"id": "c", "title": "Cozinha", "tags": ["restaurante"], "license": "CC BY 4.0", "attribution": "Fonte", "verified": False, "path": "assets/cozinha.mp4"},
        ]
        ranked = rank_assets("O cliente chegou ao caixa do restaurante", assets)
        self.assertEqual([x["asset"]["id"] for x in ranked], ["a"])
        project = self.make_project(assets=assets)
        self.assertIn("a", [s["asset_id"] for s in project["scenes"]])

    def test_rejects_path_traversal_and_fictitious_assets(self):
        project = self.make_project(assets=[{"id": "bad", "title": "Vídeo", "tags": [], "license": "CC0", "attribution": "Author", "verified": True, "path": "assets/../secret.mp4"}])
        self.assertRaises(StudioProjectError, validate_project, project)

    def test_edits_are_optimistic_and_preserve_continuity(self):
        project = self.make_project()
        first = project["scenes"][0]
        revised = update_scene(project, first["id"], {"duration_frames": first["duration_frames"] + 20}, expected_revision=1)
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(revised["total_frames"], 920)
        self.assertEqual(revised["scenes"][1]["start_frame"], revised["scenes"][0]["duration_frames"])
        self.assertRaises(StudioProjectError, update_scene, revised, first["id"], {"duration_frames": 10}, expected_revision=1)

    def test_invalid_frame_duration_is_rejected(self):
        project = self.make_project()
        project["scenes"][0]["duration_frames"] = 0
        with self.assertRaises(StudioProjectError):
            validate_project(project)

    def test_existing_render_contract_remains_unchanged(self):
        project = self.make_project()
        request = to_render_request(project)
        from scripts.render_request import validate_request
        self.assertEqual(validate_request(request)["visual_mode"], "auto")
        self.assertNotIn("schema_version", request)


class ReferenceAnalysisTests(unittest.TestCase):
    def test_parses_ffmpeg_scene_change_timestamps(self):
        text = "[Parsed_showinfo_1 @ 0x0] n: 0 pts_time:1.120 pos:23\n[Parsed_showinfo_1 @ 0x0] n: 1 pts_time:3.440 pos:111\n"
        self.assertEqual(parse_cuts(text, duration=10), [1.12, 3.44])

    def test_rhythm_uses_observed_durations_not_invented_classification(self):
        info = describe_rhythm([1.0, 2.0, 3.0], duration=8.0)
        self.assertEqual(info["shot_count"], 4)
        self.assertEqual(info["median_shot_seconds"], 1.0)
        self.assertEqual(info["cadence"], "rapido")

    def test_reference_report_labels_framing_as_heuristic(self):
        report = plan_reference({"width": 1080, "height": 1920, "duration": 20.0, "fps": 30}, [2.0, 7.0])
        self.assertEqual(report["aspect"], "9:16")
        self.assertEqual(report["framing"]["method"], "metadata_only")
        self.assertEqual(report["framing"]["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
