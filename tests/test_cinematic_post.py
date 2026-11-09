import tempfile
import unittest
import shutil
import subprocess
from pathlib import Path

from scripts.cinematic_post import (
    CinematicError, ass_safe, build_ass, check_chapters,
    cinematic_plan, render_cinematic, metadata_for_repo
)


REPOS = [
    "https://github.com/appwrite/appwrite",
    "https://github.com/payloadcms/payload",
    "https://github.com/FlowiseAI/Flowise",
    "https://github.com/docling-project/docling",
    "https://github.com/meilisearch/meilisearch",
    "https://github.com/keycloak/keycloak",
    "https://github.com/novuhq/novu",
    "https://github.com/Infisical/infisical",
]


class CinematicTests(unittest.TestCase):
    def test_timeline_eight_repositories(self):
        starts = [30, 62, 91, 123, 153, 181, 210, 253, 310]
        rows = cinematic_plan(REPOS, 331.8, starts)
        self.assertEqual([r["title"] for r in rows],
                         ["Appwrite", "Payload CMS", "Flowise", "Docling",
                          "Meilisearch", "Keycloak", "Novu", "Infisical"])
        self.assertEqual(rows[0]["start"], 30)
        self.assertEqual(rows[-1]["end"], 310)
        self.assertEqual(rows[0]["broll_seconds"], 4.5)

    def test_malformed_chapters_and_urls_rejected(self):
        for values in ([0, 4], [1] * 9, ["0"] * 9, [1,2,3,4,5,6,7,8,500]):
            with self.subTest(values=values), self.assertRaises(CinematicError):
                check_chapters(values, 8, 331.8)
        with self.assertRaises(CinematicError):
            metadata_for_repo("https://evil.example/org/repo")

    def test_pdv_repo_selects_restaurant_context_and_no_media_gate(self):
        from scripts.cinematic_post import BROLL_TERMS
        data = metadata_for_repo("https://github.com/exemplo/pdv-restaurante")
        self.assertEqual(data["category"], "pdv")
        self.assertTrue(any("restaurant" in term for term in BROLL_TERMS["pdv"]))
        self.assertEqual(metadata_for_repo("https://github.com/exemplo/obra-bim")["category"],
                         "construction")

    def test_text_safety_and_motion_graphics(self):
        plan = cinematic_plan(REPOS, 331.8)
        text = build_ass(plan, 331.8)
        self.assertIn("Inter", text)
        self.assertIn("Appwrite", text)
        self.assertIn("\\fad(", text)
        self.assertIn("8 PROJETOS", text)
        self.assertNotIn("{\\evil}", ass_safe("oi{\\evil}"))
        self.assertLess(len(text), 20000)

    def test_fabricated_news_never_appears_in_titles(self):
        rows = cinematic_plan(REPOS, 331.8)
        invented = {1: {"headline": "URGENTE: evento inventado",
                        "publisher": "Jornal falso", "published_at": "2026-11-08"}}
        plain = build_ass(rows, 331.8, news_records=invented)
        self.assertNotIn("evento inventado", plain)
        verified = {1: {**invented[1], "verified_via": "google_news_rss"}}
        trusted = build_ass(rows, 331.8, news_records=verified)
        self.assertIn("evento inventado", trusted)

    def test_five_minute_timeline_without_explicit_chapters(self):
        p = cinematic_plan(REPOS, 331.8)
        self.assertTrue(0 <= p[0]["start"] < p[-1]["end"] < 331.8)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg não disponível neste runner")
    def test_preserves_audio_when_remastering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/"original.mp4"
            output = root/"remastered.mp4"
            subprocess.run([
                "ffmpeg","-v","error","-y",
                "-f","lavfi","-i","color=c=black:s=640x360:r=12:d=4",
                "-f","lavfi","-i","sine=frequency=440:duration=4",
                "-shortest","-c:v","libx264","-c:a","aac",str(source)
            ],check=True,timeout=45)
            report = render_cinematic(source,output,[REPOS[0]],size=(640,360),
                                      quality="ultrafast")
            self.assertTrue(output.stat().st_size > 4000)
            self.assertEqual(report["resolution"],[640,360])
            check = subprocess.check_output([
                "ffprobe","-v","error","-show_entries","stream=codec_type",
                "-of","csv=p=0",str(output)
            ],text=True)
            self.assertIn("audio",check)
            self.assertIn("video",check)


if __name__ == "__main__":
    unittest.main()
