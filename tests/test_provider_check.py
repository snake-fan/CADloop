import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
import sys
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import provider_check  # noqa: E402


class ProviderCheckTests(unittest.TestCase):
    def test_env_file_parser_reads_values_without_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".env"
            path.write_text("CADLOOP_API_KEY='test-secret'\n# ignored\nBAD LINE\n", encoding="utf-8")
            values = provider_check.load_env_file(path)
        self.assertEqual(values, {"CADLOOP_API_KEY": "test-secret"})

    def test_cadloop_key_from_env_file_is_used_for_openai_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".env"
            path.write_text("CADLOOP_API_KEY=test-secret\nCADLOOP_BASE_URL=https://example.test/v1\n", encoding="utf-8")
            with mock.patch.object(provider_check, "request_json", return_value={"status": "ok", "http_status": 200}):
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    result = provider_check.main(["--env-file", str(path), "--protocol", "all"])
        self.assertEqual(result, 0)
        report = json.loads(stream.getvalue())
        self.assertEqual(report["key_env"], "CADLOOP_API_KEY")
        self.assertEqual(report["status"], "ok")
        self.assertEqual(len(report["requests"]), 3)

    def test_missing_key_is_reported_without_network_call(self):
        old = os.environ.pop("CADLOOP_TEST_PROVIDER_KEY", None)
        try:
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                result = provider_check.main(["--key-env", "CADLOOP_TEST_PROVIDER_KEY"])
            self.assertEqual(result, 2)
            report = json.loads(stream.getvalue())
            self.assertEqual(report["status"], "missing_key")
            self.assertFalse(report["key_present"])
        finally:
            if old is not None:
                os.environ["CADLOOP_TEST_PROVIDER_KEY"] = old

    def test_success_summary_does_not_retain_response_body(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, _size):
                return b'{"data":[{"id":"gpt-5.6-sol"}],"secret":"should-not-be-retained"}'

        with mock.patch.object(provider_check.urllib.request, "urlopen", return_value=Response()):
            report = provider_check.request_json("https://example.test/v1/models", "secret")
        encoded = json.dumps(report)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["response_summary"]["model_ids"], ["gpt-5.6-sol"])
        self.assertNotIn("should-not-be-retained", encoded)


if __name__ == "__main__":
    unittest.main()
