"""Deterministic scaffolding only: no CAD kernel, geometry or language model."""

import copy
from typing import Optional, Sequence

from .config import ValidationError, dimensions, object_fields
from .contracts import Action, Evaluation, Observation, PublicTask, Task


class ScriptedSmokeAgent:
    """Copy public dimensions into a mock tool, then inspect its metadata."""

    def next_action(self, task: PublicTask, history: Sequence[Observation]) -> Optional[Action]:
        if not history:
            return Action("create_box", copy.deepcopy(dict(task.public_input)))
        if len(history) == 1 and history[-1].success:
            return Action("inspect", {"object_id": history[-1].data["object_id"]})
        return None


class MockMetadataBackend:
    """Store box metadata in memory. This does not construct valid CAD geometry."""

    def __init__(self) -> None:
        self._objects = {}

    def execute(self, action: Action) -> Observation:
        try:
            if action.tool == "create_box":
                args = object_fields(dict(action.arguments), {"dimensions", "units"}, "create_box arguments")
                dims = dimensions(args["dimensions"], "create_box.dimensions")
                if args["units"] != "mm":
                    raise ValidationError("Mock backend only supports millimeters")
                object_id = "mock_box_{}".format(len(self._objects) + 1)
                self._objects[object_id] = {"shape": "box", "dimensions": dims, "units": "mm"}
                return Observation(True, {"object_id": object_id, "synthetic_only": True})
            if action.tool == "inspect":
                args = object_fields(dict(action.arguments), {"object_id"}, "inspect arguments")
                object_id = args["object_id"]
                if not isinstance(object_id, str) or object_id not in self._objects:
                    return Observation(False, error="Unknown mock object_id: {!r}".format(object_id))
                return Observation(True, {"object_id": object_id, "metadata": copy.deepcopy(self._objects[object_id]), "synthetic_only": True})
            return Observation(False, error="Unsupported mock tool: {}".format(action.tool))
        except (ValidationError, TypeError, ValueError) as exc:
            return Observation(False, error=str(exc))


class SyntheticBoxEvaluator:
    """Check metadata plumbing only. Checks do not measure geometric quality."""

    def evaluate(self, task: Task, history: Sequence[Observation]) -> Evaluation:
        inspected = next((item.data.get("metadata") for item in reversed(history) if item.success and "metadata" in item.data), None)
        checks = {
            "mock_inspection_present": inspected is not None,
            "mock_dimensions_match": inspected is not None and inspected.get("dimensions") == task.expected["expected_dimensions"],
            "mock_units_match": inspected is not None and inspected.get("units") == "mm",
        }
        return Evaluation(all(checks.values()), checks)
