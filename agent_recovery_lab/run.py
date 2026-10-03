import argparse
from collections.abc import Sequence
import hashlib
import json
from pathlib import Path
from typing import cast

from aci_patch_agent.agent import SYSTEM_PROMPT, run_task
from aci_patch_agent.client import DEFAULT_MODEL, OpenRouterClient
from aci_patch_agent.eval_tasks import EVAL_TASKS
from aci_patch_agent.experiment import execute_matrix, summarize_matrix
from aci_patch_agent.sandbox import DockerSandbox
from aci_patch_agent.tasks import Task
from aci_patch_agent.tools import TOOLS

from .contracts import FaultKind, FeedbackMode, ModelClient, RunResult, Sandbox, ToolObservation
from .faults import FaultWorkspace


FAULTS: dict[str, FaultKind] = {t.id: "test-timeout" if i < 5 else "truncated-view" for i, t in enumerate(EVAL_TASKS)}


class Arguments(argparse.Namespace):
    output: str
    task: str
    pilot: bool
    report_only: bool


def run_attempt(
    task: Task,
    condition: FeedbackMode,
    repeat: int,
    sandbox: Sandbox,
    client: ModelClient | None = None,
) -> RunResult:
    holder: list[FaultWorkspace] = []

    def factory(task: Task, sandbox: Sandbox) -> FaultWorkspace:
        workspace = FaultWorkspace(task, sandbox, fault=FAULTS[task.id], actionable=condition == "actionable")
        holder.append(workspace)
        return workspace
    # This cast describes the result schema of the pinned, untyped dependency.
    result = cast(
        RunResult,
        run_task(task, client or OpenRouterClient(), sandbox,
                 workspace_factory=factory, show_initial_source=False),
    )
    seen: set[str] = set()
    failures = repeats = 0
    for event in result["events"]:
        if "tool" not in event:
            continue
        key = json.dumps([event["tool"], event.get("arguments")], sort_keys=True)
        observation: ToolObservation = event.get("observation", {})
        failed = bool(observation.get("error")) or observation.get("passed") is False or observation.get("accepted") is False
        failures += failed
        if failed:
            repeats += key in seen
            seen.add(key)
    result.update({"fault": FAULTS[task.id], "fault_exposed": holder[0].exposed,
                   "failed_actions": failures, "repeated_actions": repeats})
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--task", choices=["all"] + [t.id for t in EVAL_TASKS], default="all",
                        help="Run only this task in both feedback modes; defaults to the full or pilot suite.")
    parser.add_argument("--pilot", action="store_true",
                        help="One attempt per condition; defaults to five scenarios unless --task selects one.")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(namespace=Arguments())
    if args.report_only:
        print(summarize_matrix(args.output))
        return
    sandbox = DockerSandbox()
    image = sandbox.preflight()
    OpenRouterClient()
    tasks: Sequence[Task] = (EVAL_TASKS[:3] + EVAL_TASKS[5:7]) if args.pilot else EVAL_TASKS
    if args.task != "all":
        tasks = [t for t in EVAL_TASKS if t.id == args.task]
    metadata = {"experiment": "tool-fault-feedback", "pilot": args.pilot,
                "agent_revision": "42a2683b643b3b9af2f034529032444accf0c849", "model": DEFAULT_MODEL,
                "temperature": 0, "max_actions": 15, "max_tokens": 1200, "max_total_tokens": 32000,
                "show_initial_source": False, "faults": {t.id: FAULTS[t.id] for t in tasks},
                "system_prompt": SYSTEM_PROMPT, "tools": TOOLS, "image": image,
                "recovery_source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))}}

    def runner(task: Task, condition: FeedbackMode, repeat: int) -> RunResult:
        return run_attempt(task, condition, repeat, sandbox)

    print(execute_matrix(args.output, tasks, ["terse", "actionable"], 1 if args.pilot else 3,
                         runner, metadata))


if __name__ == "__main__":
    main()
