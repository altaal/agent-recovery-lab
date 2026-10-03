import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from aci_patch_agent.eval_tasks import EVAL_TASKS
from agent_recovery_lab import run


class RunTest(unittest.TestCase):
    def test_selected_tasks_produce_expected_attempt_files(self) -> None:
        cases: list[tuple[list[str], set[str], int]] = [
            (["--task", "clamp"], {"clamp"}, 3),
            (["--task", "clamp", "--pilot"], {"clamp"}, 1),
            (["--task", "transpose", "--pilot"], {"transpose"}, 1),
            ([], {t.id for t in EVAL_TASKS}, 3),
            (["--task", "all"], {t.id for t in EVAL_TASKS}, 3),
            (["--pilot"], {"clamp", "safe-mean", "flatten-once", "palindrome", "parse-pairs"}, 1),
        ]
        for flags, task_ids, repeats in cases:
            with self.subTest(flags=flags), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "run"
                with patch("sys.argv", ["run", "--output", str(output), *flags]), \
                     patch.object(run, "DockerSandbox") as sandbox, \
                     patch.object(run, "OpenRouterClient"), \
                     patch.object(run, "run_attempt", return_value={
                         "passed": True, "status": "passed",
                     }) as attempt, contextlib.redirect_stdout(io.StringIO()):
                    sandbox.return_value.preflight.return_value = "test-image"
                    run.main()
                expected = {f"{task}--{mode}--{repeat}"
                            for task in task_ids for mode in ["terse", "actionable"]
                            for repeat in range(1, repeats + 1)}
                manifest = json.loads((output / "manifest.json").read_text())
                self.assertEqual({a["id"] for a in manifest["attempts"]}, expected)
                self.assertEqual(set(manifest["faults"]), task_ids)
                self.assertEqual(attempt.call_count, len(expected))
                self.assertEqual({p.stem for p in output.glob("*--*.json")}, expected)
                for attempt_id in expected:
                    result = json.loads((output / f"{attempt_id}.json").read_text())
                    self.assertEqual(result["status"], "passed")
                summary = json.loads((output / "summary.json").read_text())
                for mode in ["terse", "actionable"]:
                    self.assertEqual(summary[mode]["attempts"], len(task_ids) * repeats)

    def test_invalid_task_fails_before_docker_or_model_setup(self) -> None:
        with patch("sys.argv", ["run", "--output", "unused", "--task", "not-a-task"]), \
             patch.object(run, "DockerSandbox") as sandbox, \
             patch.object(run, "OpenRouterClient") as client, \
             contextlib.redirect_stderr(io.StringIO()), \
             self.assertRaises(SystemExit) as error:
            run.main()
        self.assertEqual(error.exception.code, 2)
        sandbox.assert_not_called()
        client.assert_not_called()
