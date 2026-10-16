import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cadbench_loader", ROOT / "scripts/cadbench.py")
CADBENCH = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CADBENCH)


class CadBenchLoaderTests(unittest.TestCase):
    def test_spec_is_pinned_and_official_run_is_unuploaded(self):
        spec = CADBENCH.load_spec()
        self.assertEqual(spec["version"], "3.0.0")
        self.assertEqual(spec["task_count"], 100)
        command = CADBENCH.official_command("codex", "gpt-5.6-sol")
        self.assertNotIn("--upload", command)
        self.assertIn("gnucleus-ai/cad-bench@v3", command)

    def test_loader_redacts_evaluator_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "tasks.jsonl"
            source.write_text(json.dumps({
                "id": "one",
                "instruction": "make a box",
                "reference": "hidden.step",
                "expected": {"volume": 1},
                "verifier": {"command": "secret"},
            }) + "\n", encoding="utf-8")
            tasks = CADBENCH.load_public_tasks(source)
        self.assertEqual(tasks[0]["task_id"], "one")
        self.assertEqual(tasks[0]["prompt"], "make a box")
        encoded = json.dumps(tasks[0], ensure_ascii=False)
        self.assertNotIn("hidden.step", encoded)
        self.assertNotIn("secret", encoded)


if __name__ == "__main__":
    unittest.main()
