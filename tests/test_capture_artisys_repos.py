"""Contract tests for the 8 real ArtiSys Github repository captures."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.capture_artisys_repos import (
    REPOSITORIES, build_capture_plan, is_allowed_asset, validate_capture_name,
    capture_report,
)


class RepoCaptureTests(unittest.TestCase):
    def test_exact_eight_carousel_repositories_in_original_order(self):
        self.assertEqual([r['name'] for r in REPOSITORIES], [
            'ERPNext', 'Twenty CRM', 'Docspell', 'Vaultwarden',
            'OpenProject', 'Paperless-ngx', 'Formbricks', 'AppFlowy',
        ])
        self.assertEqual(len({r['url'] for r in REPOSITORIES}), 8)
        self.assertTrue(all(r['url'].startswith('https://github.com/') for r in REPOSITORIES))

    def test_plan_writes_only_eight_mp4s_and_optional_github_explainer(self):
        rows = build_capture_plan(seconds=8, include_overview=False)
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0]['file'], '01-erpnext.mp4')
        self.assertEqual(rows[-1]['file'], '08-appflowy.mp4')
        self.assertEqual(len(build_capture_plan(seconds=8, include_overview=True)), 9)
        with self.assertRaises(ValueError):
            build_capture_plan(seconds=2)

    def test_restricts_navigation_hosts_and_names(self):
        self.assertTrue(is_allowed_asset('github.com'))
        self.assertTrue(is_allowed_asset('avatars.githubusercontent.com'))
        self.assertFalse(is_allowed_asset('github.com.malicious.test'))
        self.assertFalse(is_allowed_asset('localhost'))
        self.assertFalse(is_allowed_asset('127.0.0.1'))
        self.assertTrue(validate_capture_name('01-erpnext.mp4'))
        self.assertFalse(validate_capture_name('../releases/test.mp4'))

    def test_reports_are_explicit_about_partial_captures(self):
        rows = build_capture_plan(seconds=8, include_overview=False)
        with TemporaryDirectory() as tmp:
            Path(tmp, rows[0]['file']).write_bytes(b'x' * 4000)
            report = capture_report(rows, Path(tmp), errors={})
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['captured'], 1)
        self.assertEqual(report['missing'], 7)
        self.assertFalse(report['autopublish'])
        self.assertEqual(report['core_paid_api_dependency'], False)


if __name__ == '__main__':
    unittest.main()