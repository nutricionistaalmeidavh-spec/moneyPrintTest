"""Contract tests: visual builder cinematic requests use the Studio V3 renderer."""
import unittest
from scripts.render_request import validate_request, RequestError
from scripts.cinematic_studio_adapter import cinematic_request_to_studio_project
from scripts.studio_render import build_plan

REPOS=[
 "https://github.com/frappe/erpnext",
 "https://github.com/twentyhq/twenty",
 "https://github.com/chatwoot/chatwoot",
 "https://github.com/makeplane/plane",
 "https://github.com/paperless-ngx/paperless-ngx",
]

def example():
    return {
      "topic":"Cinco sistemas gratuitos no GitHub",
      "visual_mode":"github_cinematic","visual_style":"light_motion",
      "duration_seconds":300,"aspect":"16:9",
      "repo_urls":REPOS,
      "sections":[{"title":n.split("/")[-1],"repo_url":n,
        "narration":"Este sistema ajuda a organizar processos da empresa. "
                    "Uma equipe pode acompanhar tarefas e informação com mais clareza. "
                    "O projeto está disponível para instalação própria. "
                    "Consulte a licença e os requisitos antes de implantar."} for n in REPOS]
    }

class AdapterTests(unittest.TestCase):
    def test_opt_in_is_normalized_and_validated(self):
        v=validate_request(example())
        self.assertEqual(v["visual_style"],"light_motion")
        invalid=example();invalid["visual_style"]="paid_render"
        with self.assertRaises(RequestError):validate_request(invalid)

    def test_deterministic_storyboard_is_300_seconds_and_pure(self):
        a=cinematic_request_to_studio_project(validate_request(example()))
        b=cinematic_request_to_studio_project(validate_request(example()))
        self.assertEqual(a,b)
        self.assertEqual(a["visual_style"],"light_motion")
        self.assertEqual(a["total_frames"],9000)
        self.assertEqual(build_plan(a)["total_frames"],9000)
        self.assertEqual(len({s.get("repo_url") for s in a["scenes"]}),5)
        self.assertGreater(len(a["scenes"]),10)
        self.assertEqual([s["start_frame"] for s in a["scenes"]][0],0)
        self.assertEqual(sum(s["duration_frames"] for s in a["scenes"]),9000)

    def test_non_cinematic_cannot_silently_switch_renderer(self):
        v=example();v["visual_mode"]="auto";v.pop("repo_urls");v.pop("sections")
        with self.assertRaises(RequestError):validate_request(v)


if __name__=="__main__":unittest.main()
