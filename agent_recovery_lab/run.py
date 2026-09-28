import argparse
import hashlib
import json
from pathlib import Path

from aci_patch_agent.agent import SYSTEM_PROMPT, run_task
from aci_patch_agent.client import DEFAULT_MODEL, OpenRouterClient
from aci_patch_agent.eval_tasks import EVAL_TASKS
from aci_patch_agent.experiment import execute_matrix, summarize_matrix
from aci_patch_agent.sandbox import DockerSandbox
from aci_patch_agent.tools import TOOLS

from .faults import FaultWorkspace


FAULTS = {t.id: "test-timeout" if i < 5 else "truncated-view" for i, t in enumerate(EVAL_TASKS)}


def run_attempt(task, condition, repeat, sandbox, client=None):
    holder = []
    def factory(task, sandbox):
        workspace = FaultWorkspace(task, sandbox, fault=FAULTS[task.id], actionable=condition == "actionable")
        holder.append(workspace)
        return workspace
    result = run_task(task, client or OpenRouterClient(), sandbox,
                      workspace_factory=factory, show_initial_source=False)
    seen, failures, repeats = set(), 0, 0
    for event in result["events"]:
        if "tool" not in event:
            continue
        key = json.dumps([event["tool"], event.get("arguments")], sort_keys=True)
        observation = event.get("observation", {})
        failed = bool(observation.get("error")) or observation.get("passed") is False or observation.get("accepted") is False
        failures += failed
        if failed:
            repeats += key in seen
            seen.add(key)
    result.update(fault=FAULTS[task.id], fault_exposed=holder[0].exposed,
                  failed_actions=failures, repeated_actions=repeats)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--pilot", action="store_true", help="Five scenarios, one attempt per condition.")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if args.report_only:
        print(summarize_matrix(args.output))
        return
    sandbox = DockerSandbox()
    image = sandbox.preflight()
    OpenRouterClient()
    tasks = (EVAL_TASKS[:3] + EVAL_TASKS[5:7]) if args.pilot else EVAL_TASKS
    metadata = {"experiment": "tool-fault-feedback", "pilot": args.pilot,
                "agent_revision": "42a2683b643b3b9af2f034529032444accf0c849", "model": DEFAULT_MODEL,
                "temperature": 0, "max_actions": 15, "max_tokens": 1200, "max_total_tokens": 32000,
                "show_initial_source": False, "faults": {t.id: FAULTS[t.id] for t in tasks},
                "system_prompt": SYSTEM_PROMPT, "tools": TOOLS, "image": image,
                "recovery_source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))}}
    print(execute_matrix(args.output, tasks, ["terse", "actionable"], 1 if args.pilot else 3,
                         lambda t, c, r: run_attempt(t, c, r, sandbox), metadata))


if __name__ == "__main__":
    main()
