"""Type contracts for the recovery layer and its pinned agent dependency."""

from typing import Literal, NotRequired, Protocol, TypeAlias, TypedDict

from aci_patch_agent.tasks import Task


FaultKind: TypeAlias = Literal["test-timeout", "truncated-view"]
FeedbackMode: TypeAlias = Literal["terse", "actionable"]
JSONValue: TypeAlias = (
    str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
)
JSONObject: TypeAlias = dict[str, JSONValue]


class CheckFailure(TypedDict):
    case: int
    input: str
    expected: str
    actual: JSONObject


class CheckResult(TypedDict):
    passed: bool
    checks: int
    failures: list[CheckFailure]
    error: str | None


class ToolObservation(TypedDict, total=False):
    """Tools return different subsets of these fields."""

    error: str | None
    passed: bool
    accepted: bool
    submitted: bool
    source: str
    total_lines: int
    truncated: bool
    state: str
    next_action: str
    checks: int
    failures: list[CheckFailure]


class ToolEvent(TypedDict, total=False):
    """API errors and malformed calls may lack normal tool-event fields."""

    action: int
    response: int
    tool: str | None
    arguments: JSONValue
    observation: ToolObservation
    error: str


class RunResult(TypedDict):
    """The agent result, extended with recovery measurements before saving."""

    schema_version: int
    task: str
    issue: str
    created_at: str
    model: str
    show_initial_source: bool
    max_actions: int
    max_total_tokens: int
    status: str
    passed: bool
    submitted: bool
    actions: int
    model_calls: int
    prompt_tokens: int
    completion_tokens: int
    reported_cost_usd: float | None
    seconds: float
    initial_source: str
    final_source: str
    evaluation: CheckResult
    patch: str
    responses: list[JSONObject]
    events: list[ToolEvent]
    fault: NotRequired[FaultKind]
    fault_exposed: NotRequired[bool]
    failed_actions: NotRequired[int]
    repeated_actions: NotRequired[int]


class Sandbox(Protocol):
    """Real and test sandboxes support the same grading call."""

    def check(self, task: Task, source: str, *, final: bool = False) -> CheckResult:
        ...


class ModelClient(Protocol):
    """Only this client operation is required by the imported agent loop."""

    def complete(self, messages: list[JSONObject]) -> JSONObject:
        ...
