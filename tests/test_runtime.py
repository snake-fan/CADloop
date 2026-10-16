"""Focused tests of execution budgets, separation and artifact integrity."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from cadloop.config import ValidationError, load_config, load_tasks
from cadloop.contracts import Action, Observation
from cadloop.runner import run_experiment, run_task, summarize_run
from cadloop.smoke import MockMetadataBackend, ScriptedSmokeAgent, SyntheticBoxEvaluator


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiments/smoke.json"
TASKS = ROOT / "examples/smoke_tasks.jsonl"


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.task = load_tasks(TASKS)[0]

    def run_one(self, agent=None, backend=None, **kwargs):
        self.events = []
        return run_task(
            self.task, agent or ScriptedSmokeAgent(), backend or MockMetadataBackend(),
            SyntheticBoxEvaluator(), kwargs.pop("max_steps", 2),
            kwargs.pop("timeout_seconds", 10), self.events.append, **kwargs
        )

    def test_smoke_needs_two_tools_and_is_unrankable(self):
        result = self.run_one()
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.tool_calls, 2)
        self.assertEqual(len(self.events), 2)
        self.assertFalse(result.official_benchmark)
        self.assertFalse(result.evaluation.rankable)
        self.assertTrue(result.evaluation.synthetic_only)

    def test_tool_budget_is_enforced_before_extra_call(self):
        result = self.run_one(max_steps=1)
        self.assertEqual(result.status, "budget_exhausted")
        self.assertEqual(result.tool_calls, 1)
        self.assertEqual(len(self.events), 1)

    def test_agent_cannot_see_expected_values(self):
        observed = []

        class PublicOnlyAgent(ScriptedSmokeAgent):
            def next_action(self, task, history):
                observed.append(hasattr(task, "expected"))
                return super().next_action(task, history)

        result = self.run_one(agent=PublicOnlyAgent())
        self.assertEqual(result.status, "passed")
        self.assertEqual(observed, [False, False, False])

    def test_agent_cannot_mutate_evaluator_expectations(self):
        original = copy.deepcopy(self.task.expected)

        class MutatingAgent:
            def next_action(self, task, history):
                task.public_input["dimensions"]["length"] = 999
                return None

        self.assertEqual(self.run_one(agent=MutatingAgent()).status, "failed")
        self.assertEqual(self.task.expected, original)

    def test_backend_error_is_recorded(self):
        class BrokenBackend:
            def execute(self, action):
                raise RuntimeError("test failure")

        result = self.run_one(backend=BrokenBackend())
        self.assertEqual(result.status, "tool_error")
        self.assertEqual(result.tool_calls, 1)
        self.assertIn("test failure", self.events[0]["observation"]["error"])

    def test_timeout_detects_an_overlong_cooperative_step(self):
        class FakeClock:
            value = 0

            def __call__(self):
                return self.value

        clock = FakeClock()

        class SlowBackend:
            def execute(self, action):
                clock.value = 20
                return Observation(True, {"object_id": "slow"})

        result = self.run_one(backend=SlowBackend(), clock=clock)
        self.assertEqual(result.status, "timeout")
        self.assertEqual(result.tool_calls, 1)

    def test_invalid_names_and_budgets_are_rejected(self):
        original = json.loads(CONFIG.read_text())
        for section, key, invalid in (("backend", "name", "freecad"), ("budget", "max_steps", 0), ("budget", "timeout_seconds", -1)):
            config = copy.deepcopy(original)
            config[section][key] = invalid
            with self.subTest(section=section, key=key):
                with self.assertRaises(ValidationError):
                    load_config(CONFIG, json.dumps(config))

    def test_duplicate_tasks_rejected(self):
        line = TASKS.read_text().splitlines()[0]
        with self.assertRaises(ValidationError):
            load_tasks(TASKS, line + "\n" + line)

    def test_unknown_tools_fail_explicitly(self):
        result = MockMetadataBackend().execute(Action("invented_tool", {}))
        self.assertFalse(result.success)
        self.assertIn("Unsupported", result.error)


class ArtifactTests(unittest.TestCase):
    def test_run_summary_round_trip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            summary = run_experiment(CONFIG, output)
            self.assertEqual(summary["tasks_total"], 2)
            self.assertEqual(summary["tool_calls_total"], 4)
            self.assertTrue(summary["all_passed"])
            self.assertFalse(summary["rankable"])
            self.assertEqual(summary, summarize_run(output))
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "completed")
            self.assertEqual(manifest["budget"]["timeout_enforcement"], "cooperative_between_steps")
            with self.assertRaises(ValidationError):
                run_experiment(CONFIG, output)

    def test_summary_detects_modified_artifact(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            run_experiment(CONFIG, output)
            with (output / "trace.jsonl").open("a") as trace:
                trace.write("{}\n")
            with self.assertRaisesRegex(ValidationError, "hash mismatch"):
                summarize_run(output)


if __name__ == "__main__":
    unittest.main()
