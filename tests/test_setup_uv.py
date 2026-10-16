import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cadloop_setup_uv", ROOT / "scripts/setup_uv.py")
SETUP_UV = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SETUP_UV)


class SetupUvTests(unittest.TestCase):
    def test_doctor_accepts_locked_packages_and_existing_executables(self):
        with tempfile.TemporaryDirectory() as temporary:
            harbor = Path(temporary) / "harbor"
            mini = Path(temporary) / "mini"
            harbor.touch()
            mini.touch()
            report = {
                "packages": {"harbor": "0.23.0", "mini-swe-agent": "2.4.6"},
                "executables": {"harbor": str(harbor), "mini": str(mini)},
            }
            self.assertEqual(SETUP_UV.doctor_issues(report), [])

    def test_doctor_reports_missing_or_unlocked_integrations(self):
        report = {"packages": {"harbor": "0.1.0"}, "executables": {}}
        issues = SETUP_UV.doctor_issues(report)
        self.assertEqual(len(issues), 4)
        self.assertTrue(any("harbor version" in issue for issue in issues))
        self.assertTrue(any("mini-swe-agent version" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
