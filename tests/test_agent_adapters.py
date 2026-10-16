import os
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_agent_demos  # noqa: E402


class AgentAdapterTests(unittest.TestCase):
    def test_openai_base_url_is_normalized(self):
        self.assertEqual(run_agent_demos.openai_base_url("https://gateway.example"), "https://gateway.example/v1")
        self.assertEqual(run_agent_demos.openai_base_url("https://gateway.example/v1/"), "https://gateway.example/v1")

    def test_env_file_parser_reads_cadloop_key(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / ".env"
            path.write_text("CADLOOP_API_KEY='test-secret'\n", encoding="utf-8")
            self.assertEqual(run_agent_demos.load_env_file(path), {"CADLOOP_API_KEY": "test-secret"})

    def test_codex_gateway_config_uses_env_key_without_persisting_it(self):
        with tempfile.TemporaryDirectory() as outer:
            env = {"OPENAI_API_KEY": "test-secret"}
            updated, temporary = run_agent_demos.isolated_codex_env(
                env, "gpt-5.6-sol", "https://gateway.example", None
            )
            self.assertIsNotNone(temporary)
            self.assertNotEqual(updated["CODEX_HOME"], os.environ.get("CODEX_HOME"))
            config = Path(updated["CODEX_HOME"]) / "config.toml"
            content = config.read_text(encoding="utf-8")
            self.assertIn('base_url = "https://gateway.example/v1/"', content)
            self.assertNotIn("test-secret", content)
            temporary.cleanup()

    def test_explicit_codex_home_is_not_rewritten(self):
        env = {}
        updated, temporary = run_agent_demos.isolated_codex_env(
            env, "gpt-5.6-sol", "https://gateway.example/v1", "/tmp/existing-codex-home"
        )
        self.assertEqual(updated["CODEX_HOME"], "/tmp/existing-codex-home")
        self.assertIsNone(temporary)

    def test_dry_run_records_available_cli_plans_without_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "plan"
            status = run_agent_demos.main(
                [
                    "--tasks",
                    str(ROOT / "examples/cadbench_demo_tasks.jsonl"),
                    "--agents",
                    "codex",
                    "claude-code",
                    "--limit",
                    "1",
                    "--output-dir",
                    str(output),
                ]
            )
            self.assertEqual(status, 0)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertFalse(manifest["execute"])
            results = [json.loads(line) for line in (output / "results.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual([item["status"] for item in results], ["planned", "planned"])


if __name__ == "__main__":
    unittest.main()
