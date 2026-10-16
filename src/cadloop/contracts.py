"""Small contracts for later agents, CAD backends and benchmark evaluators.

PublicTask deliberately contains no evaluation expectations. A benchmark adapter
owns Task.expected and an agent receives only Task.public.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence


@dataclass(frozen=True)
class PublicTask:
    task_id: str
    instruction: str
    public_input: Mapping[str, Any]


@dataclass(frozen=True)
class Task:
    public: PublicTask
    expected: Mapping[str, Any]


@dataclass(frozen=True)
class Action:
    tool: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class Observation:
    success: bool
    data: Mapping[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass(frozen=True)
class Evaluation:
    passed: bool
    checks: Mapping[str, bool]
    synthetic_only: bool = True
    rankable: bool = False


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    status: str
    tool_calls: int
    elapsed_seconds: float
    evaluation: Optional[Evaluation] = None
    error: Optional[str] = None
    run_kind: str = "smoke"
    official_benchmark: bool = False


class Agent(Protocol):
    def next_action(
        self, task: PublicTask, history: Sequence[Observation]
    ) -> Optional[Action]:
        """Return the next tool action, or None when the task is complete."""
        ...


class Backend(Protocol):
    def execute(self, action: Action) -> Observation:
        """Execute one action and return its observable outcome."""
        ...


class Evaluator(Protocol):
    def evaluate(self, task: Task, history: Sequence[Observation]) -> Evaluation:
        """Evaluate results using benchmark-owned expectations."""
        ...
