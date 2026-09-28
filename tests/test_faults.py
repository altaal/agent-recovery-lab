import unittest

from aci_patch_agent.eval_tasks import EVAL_TASKS
from agent_recovery_lab.faults import FaultWorkspace


class Sandbox:
    calls = 0
    def check(self, *args, **kwargs):
        self.calls += 1
        return {"passed": True}


class FaultTest(unittest.TestCase):
    def test_timeout_is_once_and_does_not_run_tests(self):
        sandbox = Sandbox()
        workspace = FaultWorkspace(EVAL_TASKS[0], sandbox, fault="test-timeout", actionable=True)
        source = workspace.source
        result = workspace.execute("test", {})
        self.assertEqual(result["error"], "test_timeout")
        self.assertEqual(sandbox.calls, 0)
        self.assertEqual(source, workspace.source)
        self.assertTrue(workspace.execute("test", {})["passed"])
        self.assertEqual(sandbox.calls, 1)

    def test_feedback_changes_hints_not_fault_or_source(self):
        a = FaultWorkspace(EVAL_TASKS[0], Sandbox(), fault="test-timeout", actionable=False)
        b = FaultWorkspace(EVAL_TASKS[0], Sandbox(), fault="test-timeout", actionable=True)
        terse, full = a.execute("test", {}), b.execute("test", {})
        self.assertEqual(terse, {k: v for k, v in full.items() if k not in {"state", "next_action"}})
        self.assertEqual(a.source, b.source)

    def test_truncation_is_once_and_remaining_lines_are_retrievable(self):
        workspace = FaultWorkspace(EVAL_TASKS[5], Sandbox(), fault="truncated-view", actionable=True)
        view = workspace.execute("view", {})
        self.assertTrue(view["truncated"])
        self.assertEqual(len(view["source"].splitlines()), 1)
        self.assertIn("start=2", view["next_action"])
        second = workspace.execute("view", {"start": 2, "end": view["total_lines"]})
        self.assertNotIn("truncated", second)
        self.assertIn("return", second["source"])

    def test_no_false_exposure_if_tool_is_never_called(self):
        workspace = FaultWorkspace(EVAL_TASKS[0], Sandbox(), fault="test-timeout", actionable=True)
        workspace.execute("view", {})
        self.assertFalse(workspace.exposed)
