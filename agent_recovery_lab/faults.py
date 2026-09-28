from aci_patch_agent.tools import Workspace


class FaultWorkspace(Workspace):
    def __init__(self, task, sandbox, *, fault, actionable):
        super().__init__(task, sandbox)
        self.fault, self.actionable = fault, actionable
        self.exposed = False

    def execute(self, name, args):
        if self.fault == "test-timeout" and name == "test" and args == {} and not self.exposed:
            self.exposed = True
            result = {"error": "test_timeout", "passed": False}
            if self.actionable:
                result.update(state="No tests ran. Source unchanged.",
                              next_action="This transient timeout happened once. Retry test with empty arguments.")
            return result
        result = super().execute(name, args)
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
