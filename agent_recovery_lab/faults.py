from collections.abc import Callable
from typing import cast

from aci_patch_agent.tasks import Task
from aci_patch_agent.tools import Workspace

from .contracts import FaultKind, JSONValue, Sandbox, ToolObservation


class FaultWorkspace(Workspace):
    task: Task
    sandbox: Sandbox
    source: str
    checked: bool
    fault: FaultKind
    actionable: bool
    exposed: bool

    def __init__(
        self, task: Task, sandbox: Sandbox, *, fault: FaultKind, actionable: bool
    ) -> None:
        super().__init__(task, sandbox)
        self.fault, self.actionable = fault, actionable
        self.exposed = False

    def execute(self, name: str, args: JSONValue) -> ToolObservation:
        if self.fault == "test-timeout" and name == "test" and args == {} and not self.exposed:
            self.exposed = True
            result: ToolObservation = {"error": "test_timeout", "passed": False}
            if self.actionable:
                result.update({"state": "No tests ran. Source unchanged.",
                               "next_action": "This transient timeout happened once. Retry test with empty arguments."})
            return result
        # Describe the inherited tool contract at the untyped dependency boundary.
        execute_base = cast(Callable[[str, JSONValue], ToolObservation], super().execute)
        result = execute_base(name, args)
        if self.fault == "truncated-view" and name == "view" and "source" in result and not self.exposed:
            lines = result["source"].splitlines()
            if len(lines) > 1:
                self.exposed = True
                result["source"] = lines[0]
                result["truncated"] = True
                if self.actionable:
                    first = int(lines[0].split(":", 1)[0])
                    result["next_action"] = f"Output was truncated, not the file. Use view with start={first + 1}, end={result['total_lines']} to read the remaining lines."
        return result
