import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))
import bootstrap  # noqa: E402


class BootstrapTests(unittest.TestCase):
    def test_dry_run_does_not_create_workspace_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = bootstrap.prepare_workspace(root, dry_run=True)
            self.assertTrue(result["success"])
            self.assertTrue(all(item["status"] == "planned" for item in result["directories"]))
            self.assertFalse((root / "runs").exists())
            self.assertFalse((root / "data" / "cache").exists())

    def test_prepare_workspace_creates_only_declared_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = bootstrap.prepare_workspace(root)
            self.assertTrue(result["success"])
            self.assertTrue(all(item["status"] == "created" for item in result["directories"]))
            for relative in bootstrap.WORKSPACE_DIRECTORIES:
                self.assertTrue((root / relative).is_dir())
            self.assertFalse((root / ".env").exists())
            self.assertFalse((root / "config").exists())

    def test_doctor_credentials_are_presence_only(self):
        old = os.environ.get("CADLOOP_API_KEY")
        os.environ["CADLOOP_API_KEY"] = "test-secret-that-must-not-appear"
        try:
            report = bootstrap.doctor_report(ROOT)
        finally:
            if old is None:
                os.environ.pop("CADLOOP_API_KEY", None)
            else:
                os.environ["CADLOOP_API_KEY"] = old
        self.assertTrue(report["credentials"]["CADLOOP_API_KEY"]["present"])
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("test-secret-that-must-not-appear", encoded)

    def test_json_bootstrap_output_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as temporary:
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                status = bootstrap.main(["bootstrap", "--dry-run", "--json", "--root", temporary])
            self.assertEqual(status, 0)
            payload = json.loads(stream.getvalue())
            self.assertEqual(payload["action"], "bootstrap")
            self.assertTrue(payload["dry_run"])
            self.assertIn("doctor", payload)


if __name__ == "__main__":
    unittest.main()
