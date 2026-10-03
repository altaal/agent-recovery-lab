# Agent Recovery Lab: from the command to the saved result

## Start here: the purpose of Weeks 3 and 4

**The hypothesis is unsurprising, and this repository is a small engineering
exercise with limited research value. There is no deeper recovery algorithm hidden
inside it.** More precisely, it compares a short error:

```json
{"error": "test_timeout", "passed": false}
```

with the same error plus state information and an explicit instruction:

```json
{
  "error": "test_timeout",
  "passed": false,
  "state": "No tests ran. Source unchanged.",
  "next_action": "This transient timeout happened once. Retry test with empty arguments."
}
```

These are the observations constructed by [faults.py](agent_recovery_lab/faults.py#L27).
The second condition supplies a recovery instruction as well as state information.
It does not discover the underlying cause of a real outage: the experiment itself
creates a one-time failure and knows the next test call can run normally.

**Why do the exercise?** Practice injecting a controlled tool problem, comparing
feedback while holding the task and model fixed, recording whether the problem
was encountered, and explaining results from saved traces. Its educational value
is in building and inspecting that experiment. Its results are narrow evidence
about these tasks and messages.

| Week | Exact goal | Difference from the previous week | Completion evidence |
| --- | --- | --- | --- |
| 3 | Build the two fault behaviors and confirm a five-task pilot runs and exposes them. | Week 2 varied syntax checking. Week 3 keeps syntax checking on in both modes, introduces a timeout/truncated view, hides the initial source in both modes, and varies the feedback message. | Five tasks × two modes × one attempt = 10 records. Both modes passed 5/5; all ten encountered their fault. |
| 4 | Expand the same experiment and explain its failures and limitations. | Same fault wrapper and same feedback modes; ten tasks and three attempts per mode replace the five-task, one-attempt pilot. No new recovery algorithm or training step. | Ten tasks × two modes × three attempts = 60 records. Terse 26/30; actionable 29/30, with the qualifications below. |

The transition from Week 2 to Week 3 changes several aspects of the setup.
Compare terse with actionable **within** a recovery run; do not treat the Week 2
score and Week 3 score as a controlled before/after improvement.

### Week 3: exact command and execution path

From this repository's root, after the README setup:

```sh
python -m agent_recovery_lab.run --pilot --output runs/week3-new
```

This is five tasks, not five attempts: `clamp`, `safe-mean`, `flatten-once`,
`palindrome`, and `parse-pairs`, each in both feedback modes.

### Week 4: exact change to the same path

```sh
python -m agent_recovery_lab.run --output runs/week4-new
```

Removing `--pilot` selects all ten tasks and three repetitions per mode. Both
commands use Docker and paid model calls and require a new output directory.
`--task clamp` selects only clamp; it produces two attempts with `--pilot`, or six
without it. That targeted run is useful for inspection but is not the full weekly
experiment.

The current task-selection code is:

Source: [agent_recovery_lab/run.py](agent_recovery_lab/run.py#L81), lines 81–83. Exact excerpt:

```python
    tasks: Sequence[Task] = (EVAL_TASKS[:3] + EVAL_TASKS[5:7]) if args.pilot else EVAL_TASKS
    if args.task != "all":
        tasks = [t for t in EVAL_TASKS if t.id == args.task]
```

The same callback and matrix execute both weeks:

Source: [agent_recovery_lab/run.py](agent_recovery_lab/run.py#L91), lines 91–95. Exact excerpt:

```python
    def runner(task: Task, condition: FeedbackMode, repeat: int) -> RunResult:
        return run_attempt(task, condition, repeat, sandbox)

    print(execute_matrix(args.output, tasks, ["terse", "actionable"], 1 if args.pilot else 3,
                         runner, metadata))
```

```text
python -m agent_recovery_lab.run ...
  run.main()
    choose pilot/full tasks, then apply optional --task
    execute_matrix(..., [terse, actionable], repetitions, runner, metadata)
      write manifest with every intended attempt
      runner(task, condition, repeat) → run_attempt(...)
        factory → fresh FaultWorkspace(..., actionable=condition == "actionable")
        imported run_task(..., show_initial_source=False)
          model chooses tool → FaultWorkspace.execute(...)
            eligible first test/view → inject one response-level fault
            later calls → original Workspace behavior
          return observation → model chooses next action
          submit/budget/error → independent final Docker evaluation
        add fault_exposed, failed_actions, repeated_actions
      write <task>--<mode>--<repeat>.json
      summarize_matrix → CSV and summaries
```

For the complete annotated path, including the imported loop, Docker grading, and
JSON writes, read [Section 15](#15-exact-clamp-command-with-explanations-inside-the-code).
The [Week 3 clamp traces](#9-read-two-real-clamp-attempts-from-beginning-to-end) show what the model
actually did. In terse mode it submitted after the synthetic timeout. In actionable
mode it retried the test before submitting. Both passed final grading. The hint
changed the next action in that example; it did not improve its binary score.

### What Week 4 actually supports

The headline difference is three completed attempts. Terse had two API failures
before fault exposure, versus one for actionable. The other two terse failures were
palindrome runs that fixed the function and passed examples, then kept editing
instead of submitting. This is not evidence that the hint rescued three otherwise
identical failed repairs. [Saved failure analysis](FAILURES.md).

Actionable feedback also did not reduce mean actions (6.30 versus 6.27) or recorded
failed actions (46 versus 40). Those failed-action counters miss accepted no-op edit
loops, so they are not a complete waste metric. A stronger question, not tested
here, would be whether the agent distinguishes temporary failures worth retrying
from permanent failures where retrying cannot help.

**Week 3 succeeds as an exercise when fault injection and evidence recording work.
Week 4 succeeds as an exercise when the larger comparison and failure analysis are
complete. Neither requires the hypothesis to win.**

The sections below retain the full implementation walkthrough and historical traces.

This directory contains the experiments for **Weeks 3 and 4**. It takes the coding
agent from ACI Patch Agent, deliberately interrupts one tool operation during a
repair attempt, and measures whether the agent still submits code that passes the
final tests. The comparison changes the explanation accompanying the interruption.

The local directory is `agent-recovery-lab/`.
The published repository is [altaal/agent-recovery-lab](https://github.com/altaal/agent-recovery-lab).

“Public recovery repo and ten-attempt pilot” means the project and its saved results
are published, and its first experiment ran **five problems in two feedback modes**.
The code and results already exist. A pilot is a small initial experiment.

The experiment logic lives in two Python files, with shared type definitions in
a third:

- [run.py](agent_recovery_lab/run.py) chooses the problems and feedback modes, runs the
  existing agent, and adds measurements to its result.
- [faults.py](agent_recovery_lab/faults.py) changes one tool response per attempt. A
  “fault” here means a deliberately introduced tool problem.
- [contracts.py](agent_recovery_lab/contracts.py) defines typed result fields,
  allowed fault/feedback names, and sandbox/client interfaces.

For the exact clamp-only command, start with [Section 15: annotated code from command to results](#15-exact-clamp-command-with-explanations-inside-the-code).

Use the directory map first, then follow Sections 4–12 for the full execution path.
Sections 9 and 10 show the recorded timeout and truncated-view examples.

The model still chooses `view`, `edit`, `test`, and `submit`. It still writes the
repair. The extra code controls what happens when a tool is called; it does not
supply a repair or automatically retry on the model's behalf.

## 1. What each part of the directory contains

```text
agent-recovery-lab/
├── README.md                         Setup, commands, and headline results
├── TECHNICAL_OVERVIEW.md             This walkthrough
├── pyproject.toml                    Package definition and pinned agent dependency
├── agent_recovery_lab/
│   ├── __init__.py                    Marks this directory as a Python package
│   ├── contracts.py                   Shared types for inputs, outputs, and interfaces
│   ├── run.py                         Experiment entry point and measurements
│   └── faults.py                      The two deliberately introduced tool problems
├── tests/test_faults.py               Four implementation tests with a fake sandbox
├── tests/test_run.py                  CLI task selection and saved-output checks
├── results/
│   ├── week3-pilot/                   10 saved model attempts plus reports
│   └── week4-full/                    60 saved model attempts plus reports
├── FAILURES.md                        Explanations of the saved failed attempts
├── VERIFIED.md                        Recorded release verification
├── .github/workflows/check.yml        GitHub installation and unit checks
├── .venv/                             Installed Python environment on this machine
├── agent_recovery_lab.egg-info/       Local package installation metadata
└── .git/                              This project's own Git history
```

`.venv/` and `*.egg-info/` are ignored installation files. `results/` is committed
experiment evidence. New experiments can write to ignored `runs/` directories, which
are created when needed. An experiment refuses an output directory that already exists.

`solution.py` is not a permanent file in this repository. During `view` and `edit`,
its contents live in `Workspace.source`, a Python string. The sandbox writes that
string to a temporary `solution.py` only when executing example or final checks.

The repository reuses these parts of ACI Patch Agent:

| Imported component | Responsibility |
| --- | --- |
| `EVAL_TASKS` | Broken functions, issue descriptions, example cases, final cases |
| `run_task` | The conversation loop: ask model, execute tool, return observation |
| `Workspace` | Store the current source and implement the original four tools |
| `OpenRouterClient` | Send the conversation and tool definitions to the model |
| `DockerSandbox` | Execute the generated function and grade its behavior |
| `execute_matrix` | Declare the attempts, run them, and write their JSON files |
| `summarize_matrix` | Rebuild CSV and summary files from saved attempts |

## 2. Which version of the agent does this directory run?

The dependency in [pyproject.toml](pyproject.toml) is pinned:

```toml
dependencies = ["aci-patch-agent @ git+https://github.com/altaal/aci-patch-agent.git@42a2683b643b3b9af2f034529032444accf0c849"]
```

That installs ACI Patch Agent at commit `42a2683b643b3b9af2f034529032444accf0c849`.
It does not automatically import the current contents of the neighboring
`aci-patch-agent/` checkout. Later changes to that checkout's agent loop do not
explain these historical runs.

On this machine the imported agent is in:

```text
.venv/lib/python3.12/site-packages/aci_patch_agent/
```

The source walkthrough below uses that pinned agent version. The recovery code at
`08ad1ec` matches the hashes saved in both experiment manifests; the original pilot
and full-run records are from September 28, 2026. The inspected installed dependency
modules also match the pinned agent commit. The current recovery CLI additionally
supports `--task` and typed contracts. Section 5 preserves the historical setup;
Sections 15 and 16 show the current recovery code and its types. Excerpts from the
pinned dependency and recorded repairs retain their original signatures, including
untyped ones; they are source evidence. Recovery-owned functions, methods,
callbacks, and test doubles are fully annotated.

To inspect the actual imported file in an environment:

```sh
python -c 'import aci_patch_agent.agent; print(aci_patch_agent.agent.__file__)'
```

## 3. What Week 3 and Week 4 run

Both weeks compare these two modes:

| Mode | What the model receives when the planned problem occurs |
| --- | --- |
| `terse` | The error or shortened output, with basic status information |
| `actionable` | The same information plus a state explanation or suggested next action |

Syntax checking is **enabled in both modes**. This is a different comparison from
Week 2's `checked` versus `unchecked` editors. Both recovery modes initially hide
the source from the prompt; the model can retrieve it using `view`.

The task-to-fault assignment in [run.py](agent_recovery_lab/run.py) is:

```python
FAULTS: dict[str, FaultKind] = {t.id: "test-timeout" if i < 5 else "truncated-view" for i, t in enumerate(EVAL_TASKS)}
```

`enumerate(EVAL_TASKS)` supplies each task and its position in the fixed task list.
Positions 0–4 get the synthetic test timeout; positions 5–9 get the shortened view.

| Problem | Planned tool problem | Week 3 pilot | Week 4 full run |
| --- | --- | --- | --- |
| `clamp` | First eligible `test` returns a synthetic timeout | Yes | Yes |
| `safe-mean` | First eligible `test` returns a synthetic timeout | Yes | Yes |
| `flatten-once` | First eligible `test` returns a synthetic timeout | Yes | Yes |
| `count-words` | First eligible `test` returns a synthetic timeout | No | Yes |
| `rotate-left` | First eligible `test` returns a synthetic timeout | No | Yes |
| `palindrome` | First eligible multi-line `view` returns only its first line | Yes | Yes |
| `parse-pairs` | First eligible multi-line `view` returns only its first line | Yes | Yes |
| `running-total` | First eligible multi-line `view` returns only its first line | No | Yes |
| `strip-suffix` | First eligible multi-line `view` returns only its first line | No | Yes |
| `transpose` | First eligible multi-line `view` returns only its first line | No | Yes |

Week 3: **5 tasks × 2 modes × 1 repetition = 10 attempts**.
Week 4: **10 tasks × 2 modes × 3 repetitions = 60 attempts**.
An attempt means a fresh conversation and fresh copy of the broken source, not a
single API call. One attempt can contain several model calls and tool actions.

## 4. The complete call path

```text
python -m agent_recovery_lab.run --pilot --output runs/week3-new
  |
  +-- agent_recovery_lab/run.py: main()
      +-- parse arguments
      +-- if report-only: summarize saved files, then return
      +-- check Docker and the model credential
      +-- choose 5 tasks, 2 modes, 1 repetition
      |
      +-- aci_patch_agent/experiment.py: execute_matrix(...)
          +-- create output directory
          +-- write manifest.json listing all 10 attempts
          +-- schedule attempts with 2 worker threads
          |
          +-- run(attempt)
              +-- lambda -> agent_recovery_lab/run.py: run_attempt(...)
              |   +-- call imported run_task(..., workspace_factory=factory)
              |   |   +-- factory creates a fresh FaultWorkspace
              |   |   +-- build fresh model conversation
              |   |   +-- repeat:
              |   |   |   +-- OpenRouterClient.complete(messages)
              |   |   |   +-- model requests a tool
              |   |   |   +-- FaultWorkspace.execute(name, args)
              |   |   |   |   +-- introduce the one-time fault when eligible
              |   |   |   |   +-- otherwise use original Workspace behavior
              |   |   |   +-- append tool observation to the conversation
              |   |   +-- stop on submit, budget, or API error
              |   |   +-- DockerSandbox.check(..., final=True)
              |   |   +-- return source, trace, evaluation, and usage
              |   +-- add fault exposure and failed-action counters
              +-- add task/mode/repetition identity
              +-- write TASK--MODE--REPETITION.json
          |
          +-- summarize_matrix(output)
              +-- write results.csv, summary.json, summary.md
```

The two worker threads run separate attempts concurrently. They do not share a
conversation or cooperate on one repair. Completion order can differ from the
order in the manifest.

## 5. Command parsing and the exact ten attempts

`python -m agent_recovery_lab.run` executes the `run.py` module. Its final lines call
`main()` directly:

```python
if __name__ == "__main__":
    main()
```

Here, `run` is the module name. This project has no `cli.py` command dispatcher.
The start of `main()` used for the saved experiments was:

```python
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
```

`EVAL_TASKS[:3]` selects `clamp`, `safe-mean`, and `flatten-once`.
`EVAL_TASKS[5:7]` selects `palindrome` and `parse-pairs`.
`--pilot` combines those slices. Without `--pilot`, all ten tasks are selected.

The current CLI adds this argument:

```python
    parser.add_argument("--task", choices=["all"] + [t.id for t in EVAL_TASKS], default="all",
                        help="Run only this task in both feedback modes; defaults to the full or pilot suite.")
```

Immediately after the task-selection line above, it applies:

```python
    if args.task != "all":
        tasks = [t for t in EVAL_TASKS if t.id == args.task]
```

An explicit task overrides the suite selection, including when `--pilot` is present.
Both feedback modes still run. `--pilot` sets one repetition per mode; otherwise
there are three. Omitting `--task`, or using `--task all`, keeps the original suite
selection. Unknown task IDs are rejected before Docker or model setup.

The `--report-only` branch returns before creating a sandbox or checking the model
credential. In a live run, `sandbox.preflight()` checks Docker and the pinned image.
The first `OpenRouterClient()` checks that a credential exists; construction itself
does not call the model.

After constructing metadata, the historical implementation called:

```python
print(execute_matrix(args.output, tasks, ["terse", "actionable"], 1 if args.pilot else 3,
                     lambda t, c, r: run_attempt(t, c, r, sandbox), metadata))
```

The historical lambda is a short callback: when `execute_matrix` supplies a task
`t`, condition `c`, and repetition `r`, it calls `run_attempt(t, c, r, sandbox)`.
The current implementation uses a named, typed `runner` with the same behavior;
Section 15.2 shows its complete code.

The imported [execute_matrix implementation](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/experiment.py#L17-L26)
constructs IDs and writes the manifest before executing any attempt:

```python
def execute_matrix(output, tasks, conditions, repeats, runner, metadata, workers=2):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    attempts = [{"id": f"{task.id}--{condition}--{repeat}", "task": task.id,
                 "condition": condition, "repeat": repeat}
                for repeat in range(1, repeats + 1) for task in tasks for condition in conditions]
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "task_sha256": fingerprint(tasks),
                "agent_source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))},
                "conditions": list(conditions), "attempts": attempts, **metadata}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
```

These are all ten pilot records, in manifest order:

| Saved JSON | Planned fault | Actions actually used | Encountered planned fault | Submitted and passed |
| --- | --- | ---: | --- | --- |
| [clamp--terse--1.json](results/week3-pilot/clamp--terse--1.json) | test-timeout | 5 | Yes | Yes |
| [clamp--actionable--1.json](results/week3-pilot/clamp--actionable--1.json) | test-timeout | 6 | Yes | Yes |
| [safe-mean--terse--1.json](results/week3-pilot/safe-mean--terse--1.json) | test-timeout | 4 | Yes | Yes |
| [safe-mean--actionable--1.json](results/week3-pilot/safe-mean--actionable--1.json) | test-timeout | 5 | Yes | Yes |
| [flatten-once--terse--1.json](results/week3-pilot/flatten-once--terse--1.json) | test-timeout | 7 | Yes | Yes |
| [flatten-once--actionable--1.json](results/week3-pilot/flatten-once--actionable--1.json) | test-timeout | 6 | Yes | Yes |
| [palindrome--terse--1.json](results/week3-pilot/palindrome--terse--1.json) | truncated-view | 6 | Yes | Yes |
| [palindrome--actionable--1.json](results/week3-pilot/palindrome--actionable--1.json) | truncated-view | 6 | Yes | Yes |
| [parse-pairs--terse--1.json](results/week3-pilot/parse-pairs--terse--1.json) | truncated-view | 6 | Yes | Yes |
| [parse-pairs--actionable--1.json](results/week3-pilot/parse-pairs--actionable--1.json) | truncated-view | 6 | Yes | Yes |

For example, `clamp--actionable--1.json` means the first attempt at `clamp`, with
extra recovery guidance enabled. The final `1` is a repetition label. The callback
accepts it but does not use it to change the prompt, task inputs, or model seed.
Week 4 also produces suffixes `--2` and `--3`, each starting from the original code.

## 6. How one attempt gets its tools and prompt

The first part of [run_attempt](agent_recovery_lab/run.py) is:

```python
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
```

`factory` is a function passed into `run_task` so the caller can choose the workspace
object that implements the tools. `run_task` calls it once for the attempt.

For `clamp--actionable--1`, it creates a workspace with:

```python
# Equivalent explicit construction for this one attempt:
workspace = FaultWorkspace(
    task=clamp_task,
    sandbox=sandbox,
    fault="test-timeout",
    actionable=True,
)
```

The example above expands the actual arguments; `clamp_task` is an explanatory name
for the selected task object. `holder` retains the workspace so `run_attempt` can
read its `exposed` flag after the imported agent returns. It does not hold another
agent or conversation.

The beginning of the pinned [run_task](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/agent.py#L21-L27)
is:

```python
def run_task(task, client, sandbox, *, max_actions=15, max_total_tokens=32_000,
             workspace_factory=Workspace, show_initial_source=True):
    workspace = workspace_factory(task, sandbox)
    started = time.monotonic()
    initial = f"Task: {task.id}\n{task.issue}\n\n"
    initial += f"solution.py:\n{task.source}" if show_initial_source else "Use view to read solution.py."
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": initial}]
```

With `show_initial_source=False`, the initial user message for `clamp` is exactly:

```text
Task: clamp
Clamp a number to the inclusive range [low, high]. Raise ValueError if low > high.

Use view to read solution.py.
```

The workspace still contains the original source:

```python
def clamp(value, low, high):
    return min(value, high)
```

The model receives the system instructions and tool definitions along with the
message, but not the initial source or the additional final evaluation cases.

## 7. How the model chooses an action and receives its result

The pinned loop asks the model through `client.complete(messages)`:

```python
    while actions < max_actions:
        if prompt_tokens + completion_tokens >= max_total_tokens:
            status = "token_limit"
            break
        try:
            response = client.complete(messages)
        except ModelError as error:
            status = "api_error"
            events.append({"error": str(error)})
            break
```

[OpenRouterClient.complete](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/client.py#L25-L40)
sends the accumulated messages and tool schemas to OpenRouter. Its defaults are
`qwen/qwen3-next-80b-a3b-instruct`, temperature 0, and at most 1,200 completion tokens
per call. The model's response contains the requested tool and its arguments.

For example, the `function` object inside the saved actionable clamp test request is:

```json
{
  "name": "test",
  "arguments": "{}"
}
```

`arguments` is a JSON-encoded string. The host parses it into a dictionary. After
recording the response and its usage, the loop does:

```python
        message = response["message"]
        messages.append(message)
        calls = message.get("tool_calls") or []
```

For each requested tool call, the pinned loop executes this block:

```python
        for call in calls:
            if actions >= max_actions:
                break
            actions += 1
            name, args = None, None
            call_id = call.get("id", "missing-id") if isinstance(call, dict) else "missing-id"
            try:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])
                observation = workspace.execute(name, args)
            except (KeyError, TypeError, ValueError):
                observation = {"error": "Malformed tool call. Use a JSON object matching the tool schema."}
            events.append({"action": actions, "response": len(responses), "tool": name,
                           "arguments": args, "observation": observation})
            messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(observation)})
            if name == "submit" and observation.get("submitted"):
                submitted = True
                break
        if submitted:
            break
```

The decisive statement is `workspace.execute(name, args)`. Here `workspace` is the
`FaultWorkspace` created earlier, so execution enters `faults.py` first.
The observation is saved in `events` and added to the conversation with role
`tool`. That is how the next model call learns that a timeout or truncated output
occurred.

The loop allows at most 15 actions and checks the cumulative 32,000-token threshold
before its next model call. A final model call can take the total above that threshold.
Malformed or missing calls consume actions. A model response can contain multiple
tool calls even though the prompt asks for one, so `actions` and `model_calls` are
separate counters. Model/API errors end the loop rather than being silently retried.

## 8. The exact new tool behavior: FaultWorkspace

This is the complete implementation of [faults.py](agent_recovery_lab/faults.py):

```python
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
```

`class FaultWorkspace(Workspace)` means it inherits the original workspace's
behavior and replaces its `execute` method with the method shown above.
`super().__init__(task, sandbox)` initializes the original source and keeps the
parent's default `checked=True`. Both feedback modes therefore reject invalid
Python syntax during edits.

`execute_base` refers to the inherited `super().execute` method with its callable
type declared. Calling `execute_base(name, args)` invokes the original tool
implementation on this same workspace object. It uses the same current source; there is no second copy to sync.

**Synthetic timeout.** The first `test` with exactly `{}` as its arguments sets
`exposed=True` and returns immediately. It does not call the sandbox, wait for a
real timeout, or change the source. Once `exposed` is true, a later `test` takes the
normal path. The experiment's synthetic error is `test_timeout`; the underlying
Docker runner uses `execution_timeout` for an actual execution deadline.

**Truncated view.** The original tool runs first. If a successful `view` response
contains more than one source line and the fault has not occurred, the wrapper
keeps only the first returned line and adds `truncated=True`. `total_lines` still
reports the file's full line count. A failed view request or an already-one-line
response does not consume this fault. The file contents are never shortened.

One detail of the inherited implementation matters: a successful edit returns an
updated view using `self.execute("view", {})`
([tools.py, line 65](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/tools.py#L65)).
That internal view also calls the overridden method and can expose the truncation
fault if no earlier eligible view has done so.

`actionable` controls only the added explanation or next-action hint. It does not
execute that hint. The model chooses whether to retry, edit, submit, or do something
else.

## 9. Read two real clamp attempts from beginning to end

The [terse clamp trace](results/week3-pilot/clamp--terse--1.json) and
[actionable clamp trace](results/week3-pilot/clamp--actionable--1.json) both start
with the same broken function and finish with this same recorded repair:

```python
def clamp(value, low, high):
    if low > high:
        raise ValueError("low cannot be greater than high")
    return max(low, min(value, high))
```

Both model responses replace lines 1–2 with that function. These are the recorded
actions; the `view` notation shows the actual `start` and `end` arguments:

| Action | `clamp--terse--1` | `clamp--actionable--1` |
| --- | --- | --- |
| 1 | `view(start=1, end=10)` gets an invalid-range error; the source has 2 lines. | Same call and error. |
| 2 | `view(start=1, end=2)` reads both source lines. | Same call and output. |
| 3 | `edit(start=1, end=2, replacement=...)` installs the recorded repair above. | Same replacement and accepted result. |
| 4 | `test({})` receives the synthetic timeout with brief feedback. | `test({})` receives the same timeout plus guidance. |
| 5 | `submit({})` ends the loop. | `test({})` now executes the real examples and passes 2 checks. |
| 6 | No sixth action. | `submit({})` ends the loop. |
| After the loop | Separate final evaluation passes all 6 checks. | Separate final evaluation passes all 6 checks. |

The exact two observations at action 4 are:

```json
{
  "error": "test_timeout",
  "passed": false
}
```

```json
{
  "error": "test_timeout",
  "passed": false,
  "state": "No tests ran. Source unchanged.",
  "next_action": "This transient timeout happened once. Retry test with empty arguments."
}
```

The terse attempt **did not retry the timed-out test**. It submitted immediately.
It still passed because the independent evaluator executed the final source after
submission. The actionable attempt retried, received example-test feedback, then
submitted.

This distinguishes three facts: encountering a fault, retrying a tool, and completing
a repair. `fault_exposed=True` records only the first. The headline pass score
requires submission and passing final checks; it does not require a retry.

## 10. Read a real truncated-view attempt

In [palindrome with actionable feedback](results/week3-pilot/palindrome--actionable--1.json),
the first `view(start=1, end=10)` fails the ordinary line-range validation. That is
not the injected fault. The next `view(start=1, end=2)` succeeds and is truncated:

```json
{
  "source": "1: def is_palindrome(text):",
  "total_lines": 2,
  "truncated": true,
  "next_action": "Output was truncated, not the file. Use view with start=2, end=2 to read the remaining lines."
}
```

The model then calls `view(start=2, end=2)`, which returns:

```json
{
  "source": "2:     return text == text[::-1]",
  "total_lines": 2
}
```

It replaces line 2, calls `test`, and submits. The complete recorded sequence is:

```text
view(1, 10) -> invalid range
view(1, 2)  -> first line only, truncated=true, hint to request line 2
view(2, 2)  -> original function body
edit(2, 2) -> replace the body
test({})    -> two example checks pass
submit({}) -> loop ends; six final checks pass
```

In the [terse palindrome attempt](results/week3-pilot/palindrome--terse--1.json),
the model instead repeats `view(start=1, end=2)` to retrieve the full file. Both
attempts submit and pass the saved cases. These are recorded behaviors, not a
scripted action sequence imposed on the model, and passing the authored cases is
not proof of correctness for every possible input.

## 11. Where the tests execute and how success is decided

An ordinary `test` reaches the inherited workspace implementation:

```python
        if name == "test":
            return self.sandbox.check(self.task, self.source)
        return {"submitted": True}
```

After the agent loop stops, it independently runs final evaluation:

```python
    evaluation = sandbox.check(task, workspace.source, final=True)
    if submitted:
        status = "passed" if evaluation["passed"] else "failed_tests"
        if evaluation.get("error"):
            status = "evaluation_error"
```

The final call goes **directly to the sandbox**. It does not pass through
`FaultWorkspace.execute`, so the synthetic fault does not intercept final grading.
Final evaluation is attempted even when the loop stopped without submission.

The pinned [sandbox.check](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/sandbox.py#L30-L68)
selects cases with:

```python
    def check(self, task, source, *, final=False):
        cases = task.examples + task.evaluation if final else task.examples
```

For clamp, the inputs and expected results are:

| Call | Expected | Ordinary `test` | Final grading |
| --- | --- | --- | --- |
| `clamp(-2, 0, 10)` | `0` | Yes | Yes |
| `clamp(20, 0, 10)` | `10` | Yes | Yes |
| `clamp(5, 0, 10)` | `5` | No | Yes |
| `clamp(0, 0, 0)` | `0` | No | Yes |
| `clamp(-9, -5, -1)` | `-5` | No | Yes |
| `clamp(1, 3, 2)` | Raise `ValueError` | No | Yes |

These cases are defined in the pinned
[eval_tasks.py](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/eval_tasks.py#L7-L10).
Each sandbox invocation writes the current source and a generated test driver to
a temporary directory, then builds this Docker command:

```python
            (root / "solution.py").write_text(source)
            (root / "driver.py").write_text(driver)
            (root / "solution.py").chmod(0o644)
            (root / "driver.py").chmod(0o644)
            command = ["docker", "run", "--rm", "--name", name, "--network", "none",
                       "--user", "65534:65534", "--read-only", "--cap-drop", "ALL",
                       "--security-opt", "no-new-privileges", "--pids-limit", "32",
                       "--memory", "128m", "--cpus", "1", "--log-driver", "none",
                       "-v", f"{root}:/work:ro", "-w", "/work", self.image,
                       "python", "-I", "-B", "-S", "/work/driver.py"]
```

The driver loads `solution.py`, calls the named function for each input, and returns
actual values or exception class names as JSON. Expected answers stay on the host.
The host compares both the result's type and value, or checks the exception class.
It does not grade the model's claim of success or require a specific exception
message. A real execution timeout, invalid output, or execution error fails the check.

The overall agent result uses this expression:

```python
"passed": submitted and evaluation["passed"]
```

Consequently, code that passes every final check can still be a failed agent attempt
if the model never called `submit`. Two saved Week 4 terse palindrome attempts have
exactly that outcome; see [FAILURES.md](FAILURES.md).

## 12. How the attempt becomes a JSON file and a report

After `run_task` returns, the recovery runner calculates its additional fields:

```python
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
```

A failed action is an observation with an error, `passed=False`, or
`accepted=False`. The deliberately injected timeout counts. A truncated view alone
does not match that predicate. `repeated_actions` counts a failed call whose tool
name and arguments match a previously failed call; it does not count all repeated
successful calls or accepted no-op edits.

The imported experiment runner then attaches the identity and saves the record:

```python
    lookup = {task.id: task for task in tasks}
    def run(attempt):
        try:
            result = runner(lookup[attempt["task"]], attempt["condition"], attempt["repeat"])
        except Exception as error:
            # Preserve the attempt, but don't publish arbitrary exception strings containing paths/keys.
            result = {"passed": False, "status": "runner_error", "error_type": type(error).__name__}
        result.update(attempt)
        (output / f"{attempt['id']}.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
```

For the pilot's actionable clamp attempt, this writes
`clamp--actionable--1.json` under the output directory. The existing saved result has
these selected fields:

```json
{
  "id": "clamp--actionable--1",
  "task": "clamp",
  "condition": "actionable",
  "repeat": 1,
  "fault": "test-timeout",
  "fault_exposed": true,
  "submitted": true,
  "passed": true,
  "actions": 6,
  "model_calls": 6,
  "failed_actions": 2,
  "repeated_actions": 0,
  "evaluation": {
    "passed": true,
    "checks": 6,
    "failures": [],
    "error": null
  }
}
```

The complete record additionally contains:

| Field | Contents |
| --- | --- |
| `initial_source`, `final_source` | The starting and ending Python function text |
| `patch` | A unified diff between those two source strings |
| `responses` | Model response messages, requested tools, provider metadata, and token usage |
| `events` | Each executed action's arguments and the observation returned to the model |
| `evaluation` | Independent final-check result, check count, failures, and execution error |
| `prompt_tokens`, `completion_tokens`, `reported_cost_usd`, `seconds` | Recorded usage and duration for the attempt |

`manifest.json` records all declared attempt IDs, settings, fault assignments, source
hashes, and container identity. `summarize_matrix` reads that manifest, loads each
attempt file, and produces `results.csv`, `summary.json`, and `summary.md`.
An absent declared file becomes a failed `missing_attempt` row. Exceptions caught
by `execute_matrix` become failed `runner_error` records. Neither is dropped from
the denominator.

## 13. What the saved results establish

| Experiment | Terse | Actionable | Attempts that encountered a fault |
| --- | --- | --- | --- |
| [Week 3 pilot](results/week3-pilot/summary.md) | 5/5 passed | 5/5 passed | 5 terse, 5 actionable |
| [Week 4 full run](results/week4-full/summary.md) | 26/30 passed | 29/30 passed | 28 terse, 29 actionable |

The pilot establishes that the setup runs and the planned faults occur. Both
conditions reached 100%, so its pass rate does not distinguish them. The clamp
traces still show a difference in whether the model retried the failed test call.

In the full run, three attempts failed on an API transport/response error before
encountering the injected fault. Two additional terse attempts produced code that
passed final tests but exhausted the action budget without submission. Those five
failures remain in the headline totals. The saved API error does not identify a
specific provider or network root cause.

The full-run mean actions were 6.27 for terse and 6.30 for actionable. Thus the higher
completion rate did not come with fewer actions. These are small, authored tasks
with synthetic single-event faults. The result does not establish a general recovery
guarantee. Detailed failure records are linked from [FAILURES.md](FAILURES.md).

## 14. Commands: inspect, check, report, or run a new experiment

Use the environment installed for this project. On this machine:

```sh
cd agent-recovery-lab
. .venv/bin/activate
```

For a fresh clone, first follow [README setup](README.md#run).

Inspect the saved evidence without model calls:

```sh
cat results/week3-pilot/summary.md
python -m json.tool results/week3-pilot/clamp--actionable--1.json
```

Check the wrapper's implementation without Docker or a model key:

```sh
python -m unittest discover -s tests -v
```

The four [tests](tests/test_faults.py) check that the timeout happens once and does
not run tests, that feedback differences do not change the fault or source, that
truncated lines remain retrievable, and that an unencountered fault is not reported
as exposed. Their fake sandbox checks wrapper behavior; these unit tests do not
measure a model's repair ability.

Rebuild existing reports from saved records:

```sh
python -m agent_recovery_lab.run --report-only --output results/week3-pilot
python -m agent_recovery_lab.run --report-only --output results/week4-full
```

These commands rewrite the three report files from the existing manifest and
attempt JSONs. They do not ask the model to repair anything or rerun final evaluation.
They require neither Docker nor a model key.

Start a new Week 3 pilot or Week 4 full experiment:

```sh
python -m agent_recovery_lab.run --pilot --output runs/week3-new
python -m agent_recovery_lab.run --output runs/week4-new
```

These commands require Docker, the documented image, and `OPENROUTER_API_KEY`.
They make live paid model calls. Choose a new output directory for every experiment.
The first command schedules ten fresh attempts; the second schedules sixty.
Neither command trains a model.

Run only clamp in both feedback modes:

```sh
python -m agent_recovery_lab.run --task clamp --output runs/clamp
```

This schedules six attempts: `clamp--terse--1.json` through `clamp--terse--3.json`,
and `clamp--actionable--1.json` through `clamp--actionable--3.json`.
Add `--pilot` to schedule only repetition 1 in each mode (two attempts).
The [CLI tests](tests/test_run.py) exercise selection and file generation with fake
attempts, without Docker or model calls.

## 15. Exact clamp command, with explanations inside the code

This walkthrough follows this exact command from the project directory, using
this project's activated virtual environment:

```sh
python -m agent_recovery_lab.run --pilot --output runs/pilot-new --task clamp
```

It schedules **two fresh repair attempts on the same broken clamp function**:
one with `terse` feedback and one with `actionable` feedback. Each attempt gets
its own conversation, source string, and one-time fault state.

**Both attempts get the fake test timeout.** The modes change the explanation
returned with that timeout. This command does not assign a truncated view to clamp.

The source excerpts below preserve the executable statements from the current
recovery code and its installed ACI Patch Agent dependency. Added `#` comments
explain what happens for this command. The dependency excerpts match pinned commit
`42a2683b643b3b9af2f034529032444accf0c849`. These are pieces of the named source
files, not a second standalone implementation.

The command determines the task, feedback modes, limits, and fault assignment.
The model chooses its actual tool calls and repair. Section 15.9 shows complete
recorded clamp tool sequences from September 28 as examples; those are not
claimed to be the output of a newly executed `runs/pilot-new` experiment.

The sections follow this flow:

1. Load clamp and choose its fault.
2. Parse the command and check prerequisites.
3. Declare and schedule two attempts.
4. Create a fresh workspace and conversation for each.
5. Ask the model for an action, execute it, and return its observation.
6. Follow both recorded clamp attempts through submission.
7. Run final checks, save the attempts, and build reports.

### 15.1 Load the task: what clamp must do and what starts broken

A `Task` holds the issue, starting code, and checks. A `Case` holds one input
and its expected result or expected exception.

Source: [aci_patch_agent/tasks.py](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/tasks.py#L3), lines 3–20.

<!-- clamp-source: .venv/lib/python3.12/site-packages/aci_patch_agent/tasks.py:3:20 -->
```python
from dataclasses import dataclass


# Frozen task descriptions are not mutated during an attempt.
@dataclass(frozen=True)
class Case:
    # Arguments to pass to clamp, such as (-2, 0, 10).
    args: tuple
    # Expected returned value, such as 0.
    expected: object = None
    # Alternatively, an expected exception class name, such as "ValueError".
    raises: str | None = None


@dataclass(frozen=True)
class Task:
    # The command selects this ID: "clamp".
    id: str
    # The evaluator looks up this function name inside solution.py: "clamp".
    function: str
    # The requirement sent to the model.
    issue: str
    # The starting broken Python code, copied into each workspace.
    source: str
    # Cases the model can run with test().
    examples: tuple[Case, ...]
    # Additional final cases; final grading includes these AND the examples.
    evaluation: tuple[Case, ...]
```

Here is the complete clamp entry inside the `EVAL_TASKS` tuple. Only the other
nine task entries are omitted; `--task clamp` excludes them from the attempts.
The positional arguments correspond to the `Task` fields above.

Source: [aci_patch_agent/eval_tasks.py](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/eval_tasks.py#L7), lines 7–10.

<!-- clamp-source: .venv/lib/python3.12/site-packages/aci_patch_agent/eval_tasks.py:7:10 -->
```python
    # Task(id, function, issue, source, examples, evaluation).
    # The issue requires clamping AND rejecting invalid bounds.
    Task("clamp", "clamp", "Clamp a number to the inclusive range [low, high]. Raise ValueError if low > high.",
         # Broken code: min(value, high) caps the upper bound but ignores low.
         # clamp(-2, 0, 10) returns -2; it should return 0.
         "def clamp(value, low, high):\n    return min(value, high)\n",
         # Two examples: below the lower bound and above the upper bound.
         (Case((-2, 0, 10), 0), Case((20, 0, 10), 10)),
         # Four extra final checks: inside the range, equal bounds,
         # a negative range, and invalid bounds requiring ValueError.
         (Case((5, 0, 10), 5), Case((0, 0, 0), 0), Case((-9, -5, -1), -5), Case((1, 3, 2), raises="ValueError"))),
```

The module builds its fault assignment from the full task list before the
command's task filter runs.

Source: [agent_recovery_lab/run.py](agent_recovery_lab/run.py#L20), lines 20–20.

<!-- clamp-source: agent_recovery_lab/run.py:20:20 -->
```python
# enumerate yields (0, clamp), (1, safe-mean), and so on.
# For clamp, i == 0: i < 5 is True, so FAULTS["clamp"] becomes "test-timeout".
# Tasks at positions 5 through 9 get "truncated-view". Selecting clamp later keeps its assignment.
FAULTS: dict[str, FaultKind] = {t.id: "test-timeout" if i < 5 else "truncated-view" for i, t in enumerate(EVAL_TASKS)}
```

### 15.2 Enter main, parse the command, and select clamp

These imports identify the implementations used below. The installed dependency,
rather than the neighboring development checkout, supplies the agent.

Source: [agent_recovery_lab/run.py](agent_recovery_lab/run.py#L1), lines 1–17.

<!-- clamp-source: agent_recovery_lab/run.py:1:17 -->
```python
import argparse
from collections.abc import Sequence
import hashlib
import json
from pathlib import Path
from typing import cast

# Import the conversation loop and its shared instructions.
from aci_patch_agent.agent import SYSTEM_PROMPT, run_task
from aci_patch_agent.client import DEFAULT_MODEL, OpenRouterClient
# Import the ten task records, including clamp.
from aci_patch_agent.eval_tasks import EVAL_TASKS
# execute_matrix schedules attempts; summarize_matrix rebuilds reports.
from aci_patch_agent.experiment import execute_matrix, summarize_matrix
from aci_patch_agent.sandbox import DockerSandbox
from aci_patch_agent.tasks import Task
from aci_patch_agent.tools import TOOLS

from .contracts import FaultKind, FeedbackMode, ModelClient, RunResult, Sandbox, ToolObservation
# Import the local subclass that adds a deliberate tool problem.
from .faults import FaultWorkspace
```

Source: [agent_recovery_lab/run.py](agent_recovery_lab/run.py#L98), lines 98–99.

<!-- clamp-source: agent_recovery_lab/run.py:98:99 -->
```python
# python -m agent_recovery_lab.run sets __name__ to "__main__".
if __name__ == "__main__":
    # Enter main() here. Importing this module alone does not call main().
    main()
```

Source: [agent_recovery_lab/run.py](agent_recovery_lab/run.py#L23), lines 23–27.

<!-- clamp-source: agent_recovery_lab/run.py:23:27 -->
```python
# argparse fills these fields; declaring them makes their types explicit.
class Arguments(argparse.Namespace):
    # The new output directory path from --output.
    output: str
    # The task ID from --task, or "all".
    task: str
    # Whether --pilot was supplied.
    pilot: bool
    # Whether --report-only was supplied.
    report_only: bool
```

Source: [agent_recovery_lab/run.py](agent_recovery_lab/run.py#L66), lines 66–95.

<!-- clamp-source: agent_recovery_lab/run.py:66:95 -->
```python
def main() -> None:
    parser = argparse.ArgumentParser()
    # args.output becomes "runs/pilot-new".
    parser.add_argument("--output", required=True)
    # args.task becomes "clamp"; argparse rejects unknown IDs.
    parser.add_argument("--task", choices=["all"] + [t.id for t in EVAL_TASKS], default="all",
                        help="Run only this task in both feedback modes; defaults to the full or pilot suite.")
    # args.pilot becomes True.
    parser.add_argument("--pilot", action="store_true",
                        help="One attempt per condition; defaults to five scenarios unless --task selects one.")
    # Not supplied, so args.report_only stays False.
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(namespace=Arguments())
    # Skip this branch: this command starts attempts rather than rebuilding old reports.
    if args.report_only:
        print(summarize_matrix(args.output))
        return
    # Create a DockerSandbox configuration object shared by the two attempts.
    sandbox = DockerSandbox()
    # Check Docker and the pinned image; no clamp checks run yet.
    image = sandbox.preflight()
    # Check that the model credential exists. Constructing a client makes no API call.
    OpenRouterClient()
    # pilot=True first selects five tasks.
    tasks: Sequence[Task] = (EVAL_TASKS[:3] + EVAL_TASKS[5:7]) if args.pilot else EVAL_TASKS
    # "clamp" != "all", so apply the explicit task selection.
    if args.task != "all":
        # Replace that five-task selection with exactly one task: clamp.
        tasks = [t for t in EVAL_TASKS if t.id == args.task]
    # Record settings and source fingerprints in the manifest.
    metadata = {"experiment": "tool-fault-feedback", "pilot": args.pilot,
                "agent_revision": "42a2683b643b3b9af2f034529032444accf0c849", "model": DEFAULT_MODEL,
                # These are recorded settings; run_task and the client enforce their matching defaults below.
                "temperature": 0, "max_actions": 15, "max_tokens": 1200, "max_total_tokens": 32000,
                # For this command, faults is {"clamp": "test-timeout"}.
                # The first prompt omits the source in both modes.
                "show_initial_source": False, "faults": {t.id: FAULTS[t.id] for t in tasks},
                "system_prompt": SYSTEM_PROMPT, "tools": TOOLS, "image": image,
                # Record hashes of the recovery Python files to identify their exact contents.
                "recovery_source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))}}

    # A named, typed callback replaces the earlier lambda with the same forwarding behavior.
    def runner(task: Task, condition: FeedbackMode, repeat: int) -> RunResult:
        return run_attempt(task, condition, repeat, sandbox)

    # One task x two modes x one repetition = TWO attempts.
    # The pilot flag chooses 1; without it this expression chooses 3.
    # One task x two feedback modes x one repetition schedules two attempts.
    # The pilot flag chooses 1 here; without it the expression chooses 3.
    print(execute_matrix(args.output, tasks, ["terse", "actionable"], 1 if args.pilot else 3,
                         # The callback receives task=clamp, condition=the mode, and repeat=1.
                         runner, metadata))
```

```python
# Values for this command:
# args.output      == "runs/pilot-new"
# args.task        == "clamp"
# args.pilot       == True
# args.report_only == False
# tasks            == [the clamp Task record]
# conditions       == ["terse", "actionable"]
# repeats          == 1
# FAULTS["clamp"]   == "test-timeout"
```

The complete Docker setup path is:

Source: [aci_patch_agent/sandbox.py](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/sandbox.py#L11), lines 11–28.

<!-- clamp-source: .venv/lib/python3.12/site-packages/aci_patch_agent/sandbox.py:11:28 -->
```python
# Use an exact image digest rather than a moving Python image tag.
DEFAULT_IMAGE = "python@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9"


class DockerSandbox:
    # Actual code execution later has a default 10-second deadline.
    def __init__(self, image=DEFAULT_IMAGE, timeout=10):
        self.image, self.timeout = image, timeout

    def preflight(self):
        # Check the daemon, then inspect the required local image.
        for args in (["docker", "info"], ["docker", "image", "inspect", self.image]):
            try:
                # Each prerequisite check has a separate 15-second timeout.
                result = subprocess.run(args, capture_output=True, timeout=15)
            # Failure to execute Docker or a timed-out check stops setup.
            except (OSError, subprocess.TimeoutExpired) as error:
                raise RuntimeError("Docker is unavailable. Start Docker and pull the documented image.") from error
            # A nonzero exit code also stops setup.
            if result.returncode:
                raise RuntimeError(f"Docker or image {self.image} is unavailable. See README setup.")
        # The last successful command inspected the image; parse its identity.
        data = json.loads(result.stdout)
        # Return image identity for manifest metadata.
        return {"image": self.image, "image_id": data[0]["Id"], "repo_digests": data[0].get("RepoDigests", []),
                "architecture": data[0]["Architecture"]}
```

### 15.3 Declare and schedule the two attempts

The "matrix" is the list of task, feedback mode, and repetition combinations.

Source: [aci_patch_agent/experiment.py](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/experiment.py#L13), lines 13–42.

<!-- clamp-source: .venv/lib/python3.12/site-packages/aci_patch_agent/experiment.py:13:42 -->
```python
def fingerprint(tasks):
    # Hash the selected task records, including their source and checks.
    return hashlib.sha256(repr([asdict(t) for t in tasks]).encode()).hexdigest()


def execute_matrix(output, tasks, conditions, repeats, runner, metadata, workers=2):
    output = Path(output)
    # Create runs/pilot-new. exist_ok=False rejects an existing directory.
    output.mkdir(parents=True, exist_ok=False)
    # Build one ID for each combination.
    attempts = [{"id": f"{task.id}--{condition}--{repeat}", "task": task.id,
                 "condition": condition, "repeat": repeat}
                # Here repeat is 1, task is clamp, and condition is terse or actionable.
                for repeat in range(1, repeats + 1) for task in tasks for condition in conditions]
    # Declare attempts and fingerprints before requesting any model actions.
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "task_sha256": fingerprint(tasks),
                "agent_source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))},
                "conditions": list(conditions), "attempts": attempts, **metadata}
    # Write runs/pilot-new/manifest.json.
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    # Map "clamp" to its Task record.
    lookup = {task.id: task for task in tasks}
    # This inner function runs once per attempt.
    def run(attempt):
        try:
            # Call the callback from main(), which enters run_attempt(clamp, mode, 1, sandbox).
            result = runner(lookup[attempt["task"]], attempt["condition"], attempt["repeat"])
        # An exception still produces a failed attempt record.
        except Exception as error:
            # Preserve the attempt, but don't publish arbitrary exception strings containing paths/keys.
            result = {"passed": False, "status": "runner_error", "error_type": type(error).__name__}
        # Attach id, task, condition, and repeat to the result.
        result.update(attempt)
        # Save clamp--terse--1.json or clamp--actionable--1.json.
        (output / f"{attempt['id']}.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    # Default workers=2 allows the independent attempts to overlap.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # Schedule both attempts; their conversations and sources are separate.
        futures = [pool.submit(run, attempt) for attempt in attempts]
        # Collect in completion order, which can differ from the manifest order.
        for index, future in enumerate(as_completed(futures), 1):
            result = future.result()
            # Print progress with the actual status returned by that attempt.
            print(f"{index}/{len(attempts)} {result['id']}: {result['status']}", flush=True)
    # When both workers finish, build reports from saved records.
    return summarize_matrix(output)
```

The manifest contains exactly these attempt entries:

```python
[
    # Independent attempt A: brief feedback, repetition 1.
    {"id": "clamp--terse--1", "task": "clamp", "condition": "terse", "repeat": 1},
    # Independent attempt B: explanation plus retry guidance, repetition 1.
    {"id": "clamp--actionable--1", "task": "clamp", "condition": "actionable", "repeat": 1},
]
```

### 15.4 Create a fresh workspace for each feedback mode

The scheduler invokes `run_attempt` separately for terse and actionable.
Both start with the same broken source. Each gets its own `exposed=False` flag,
so the two attempts can each encounter their own first-test timeout.

Source: [agent_recovery_lab/run.py](agent_recovery_lab/run.py#L30), lines 30–63.

<!-- clamp-source: agent_recovery_lab/run.py:30:63 -->
```python
def run_attempt(
    task: Task,
    condition: FeedbackMode,
    repeat: int,
    sandbox: Sandbox,
    client: ModelClient | None = None,
) -> RunResult:
    # Keep a reference to the workspace so exposure can be reported afterward.
    holder: list[FaultWorkspace] = []

    # run_task calls this factory once for this attempt.
    def factory(task: Task, sandbox: Sandbox) -> FaultWorkspace:
        # For BOTH attempts, fault="test-timeout".
        # Terse makes actionable=False; actionable makes actionable=True.
        workspace = FaultWorkspace(task, sandbox, fault=FAULTS[task.id], actionable=condition == "actionable")
        # Retain this workspace so its exposure flag can be reported after the run.
        holder.append(workspace)
        return workspace
    # Run the full conversation and final grading with a fresh client.
    # The factory adds the fault; show_initial_source=False omits the code from the first prompt.
    # RunResult describes the dictionary returned by the pinned dependency.
    # cast adds no runtime validation and does not copy the result.
    # This cast describes the result schema of the pinned, untyped dependency.
    result = cast(
        RunResult,
        run_task(task, client or OpenRouterClient(), sandbox,
                 workspace_factory=factory, show_initial_source=False),
    )
    # Reached after the agent loop AND final grading; now count failed actions.
    seen: set[str] = set()
    # repeats counts repeated failed calls, not the attempt repetition number.
    failures = repeats = 0
    for event in result["events"]:
        # Skip events without a tool field, such as an API-error event.
        if "tool" not in event:
            continue
        # Identify a call by tool name and arguments.
        key = json.dumps([event["tool"], event.get("arguments")], sort_keys=True)
        observation: ToolObservation = event.get("observation", {})
        # Error responses, failed tests, and rejected edits count as failed actions.
        failed = bool(observation.get("error")) or observation.get("passed") is False or observation.get("accepted") is False
        # True adds 1, so the fabricated timeout contributes one failed action.
        failures += failed
        if failed:
            # Only a failed call matching an earlier failed call counts as repeated.
            repeats += key in seen
            # Remember the failed call; a later successful retry does not increment repeated failures.
            seen.add(key)
    # Read whether this workspace actually injected its fault.
    # If no eligible test was called, fault_exposed remains False.
    result.update({"fault": FAULTS[task.id], "fault_exposed": holder[0].exposed,
                   "failed_actions": failures, "repeated_actions": repeats})
    # Return to execute_matrix, which attaches the ID and saves the JSON.
    return result
```

### 15.5 Build the first messages and run the model/tool loop

The full pinned agent loop below shows prompt construction, tool dispatch,
stopping conditions, final grading, and the returned record. The client,
workspace, and sandbox calls are expanded in subsequent sections.

Source: [aci_patch_agent/agent.py](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/agent.py#L12), lines 12–96.

<!-- clamp-source: .venv/lib/python3.12/site-packages/aci_patch_agent/agent.py:12:96 -->
```python
# Both modes receive these same system instructions describing the tools.
SYSTEM_PROMPT = """You repair one small Python function in solution.py.
Use view to read numbered lines, edit to replace an inclusive range, test to run
examples, and submit when finished. Make exactly one tool call per response.
Tool observations describe the actual current state. Correct a refused edit using
that feedback. Tests check only examples; implement the entire issue specification.
Keep the named function and signature. Use only Python's standard library.
You cannot edit the evaluator. Submit the code, not a verbal claim of success."""


# Default limits: 15 actions and a stopping threshold of 32,000 reported tokens.
def run_task(task, client, sandbox, *, max_actions=15, max_total_tokens=32_000,
             workspace_factory=Workspace, show_initial_source=True):
    # Call the recovery factory to get this attempt's fresh FaultWorkspace.
    workspace = workspace_factory(task, sandbox)
    started = time.monotonic()
    # Build the user message from the ID "clamp" and its issue description.
    initial = f"Task: {task.id}\n{task.issue}\n\n"
    # False selects "Use view to read solution.py." instead of pasting task.source.
    initial += f"solution.py:\n{task.source}" if show_initial_source else "Use view to read solution.py."
    # Both modes begin with identical messages.
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": initial}]
    # Keep tool events separately from raw model responses.
    events, responses = [], []
    actions = prompt_tokens = completion_tokens = 0
    costs = []
    # Exhausting the action budget without submission leaves action_limit status.
    status = "action_limit"
    submitted = False
    # Repeat: ask the model, execute its requested tool, append the observation.
    while actions < max_actions:
        # Check reported tokens BEFORE another request; the previous call can overshoot this threshold.
        if prompt_tokens + completion_tokens >= max_total_tokens:
            status = "token_limit"
            break
        try:
            # Send the current conversation to the model.
            response = client.complete(messages)
        # A ModelError stops the loop as api_error.
        except ModelError as error:
            status = "api_error"
            events.append({"error": str(error)})
            break
        # Save the response and then accumulate its reported usage.
        responses.append(response)
        usage = response.get("usage", {})
        prompt_tokens += usage.get("prompt_tokens", 0) or 0
        completion_tokens += usage.get("completion_tokens", 0) or 0
        if isinstance(usage.get("cost"), (float, int)):
            costs.append(usage["cost"])
        # Read the returned assistant message, including its tool calls.
        message = response["message"]
        # Append the assistant request before the tool observation.
        messages.append(message)
        calls = message.get("tool_calls") or []
        # No usable tool-call list: consume an action and send corrective feedback.
        if not isinstance(calls, list) or not calls:
            actions += 1
            observation = {"error": "No tool call received; call view, edit, test, or submit."}
            events.append({"action": actions, "tool": None, "observation": observation})
            messages.append({"role": "user", "content": json.dumps(observation)})
            continue
        # Handle the returned calls; the prompt requests one, but the loop accepts a list.
        for call in calls:
            if actions >= max_actions:
                break
            # Consume one action for each dispatched call.
            actions += 1
            name, args = None, None
            call_id = call.get("id", "missing-id") if isinstance(call, dict) else "missing-id"
            try:
                # Read the tool name, such as "view", "edit", "test", or "submit".
                name = call["function"]["name"]
                # Decode its arguments from JSON.
                args = json.loads(call["function"]["arguments"])
                # Call FaultWorkspace.execute; this is where the first test can be intercepted.
                observation = workspace.execute(name, args)
            # Malformed call structure or arguments produce an error observation.
            except (KeyError, TypeError, ValueError):
                observation = {"error": "Malformed tool call. Use a JSON object matching the tool schema."}
            # Record the executed tool, arguments, and result.
            events.append({"action": actions, "response": len(responses), "tool": name,
                           "arguments": args, "observation": observation})
            # Put the tool result in messages so the NEXT model request includes it.
            # A next_action hint is text for the model, not a command executed here.
            messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(observation)})
            # Only an accepted submit call sets submitted=True.
            if name == "submit" and observation.get("submitted"):
                submitted = True
                break
        if submitted:
            break
    # After the loop, grade the current code DIRECTLY in Docker.
    # final=True runs all six clamp cases and bypasses the fault override.
    evaluation = sandbox.check(task, workspace.source, final=True)
    if submitted:
        # For a submitted attempt, final checks determine passed versus failed_tests.
        status = "passed" if evaluation["passed"] else "failed_tests"
        # A grading error produces evaluation_error.
        if evaluation.get("error"):
            status = "evaluation_error"
    # Build the record that run_attempt receives.
    return {"schema_version": 1, "task": task.id, "issue": task.issue,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": getattr(client, "model", "scripted-test"),
            "show_initial_source": show_initial_source,
            "max_actions": max_actions, "max_total_tokens": max_total_tokens,
            # Success requires BOTH submitting and passing the final checks.
            "status": status, "passed": submitted and evaluation["passed"],
            "submitted": submitted, "actions": actions, "model_calls": len(responses),
            "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
            "reported_cost_usd": sum(costs) if costs and len(costs) == len(responses) else None,
            # Retain the starting source for inspection; this does not mean it was in the initial prompt.
            "seconds": round(time.monotonic() - started, 3), "initial_source": task.source,
            # Save the final source and independent grading result.
            "final_source": workspace.source, "evaluation": evaluation,
            # Create the patch by comparing the starting and ending source.
            "patch": "".join(difflib.unified_diff(task.source.splitlines(True), workspace.source.splitlines(True),
                                                fromfile="a/solution.py", tofile="b/solution.py")),
            # Save the response history and tool-event history.
            "responses": responses, "events": events}
```

The initial user message from those lines is exactly:

```text
Task: clamp
Clamp a number to the inclusive range [low, high]. Raise ValueError if low > high.

Use view to read solution.py.
```

The system instructions and tool definitions tell the model how to request the
code. It first sees that code when a returned tool observation contains it.

### 15.6 Send the conversation and tool schemas to the model

The constructor checks the key and sets defaults. `complete` makes the actual
network request for the next action.

Source: [aci_patch_agent/client.py](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/client.py#L10), lines 10–45.

<!-- clamp-source: .venv/lib/python3.12/site-packages/aci_patch_agent/client.py:10:45 -->
```python
# Both modes use the same hosted model.
DEFAULT_MODEL = "qwen/qwen3-next-80b-a3b-instruct"


class ModelError(RuntimeError):
    pass


class OpenRouterClient:
    # Both use temperature=0 and at most 1,200 completion tokens per call.
    def __init__(self, model=DEFAULT_MODEL, max_tokens=1200, temperature=0, tools=None):
        # Read the credential from the environment; it is not prompt text.
        self.key = os.environ.get("OPENROUTER_API_KEY")
        # An absent key stops client construction.
        if not self.key:
            raise ModelError("Set OPENROUTER_API_KEY in your environment.")
        self.model, self.max_tokens, self.temperature = model, max_tokens, temperature
        # Use the same four tool schemas in both modes.
        self.tools = tools if tools is not None else TOOLS

    def complete(self, messages):
        # Send the current conversation, including prior tool results.
        body = {"model": self.model, "messages": messages, "tools": self.tools,
                # Ask the model for a tool call; the agent still validates its response.
                "tool_choice": "required", "temperature": self.temperature,
                "max_tokens": self.max_tokens}
        # Construct the API request for the next model action.
        req = request.Request("https://openrouter.ai/api/v1/chat/completions",
                              data=json.dumps(body).encode(),
                              headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"})
        try:
            # This real HTTP timeout is 90 seconds, separate from the fake test_timeout.
            with request.urlopen(req, timeout=90) as response:
                data = json.load(response)
            # Read the first returned assistant message.
            message = data["choices"][0]["message"]
            if not isinstance(message, dict):
                raise ValueError("invalid message")
            # Return the fields used by the agent loop and its saved record.
            return {"message": {k: message[k] for k in ("role", "content", "tool_calls") if k in message},
                    "usage": data.get("usage") or {}, "model": data.get("model", self.model),
                    "provider": data.get("provider"), "id": data.get("id")}
        # Convert HTTP failures to sanitized ModelError values.
        except error.HTTPError as failure:
            # Provider error bodies may echo requests; never log them or the Authorization header.
            raise ModelError(f"api_http_{failure.code}") from None
        # Transport or response-format failures also become ModelError.
        # There is no automatic API retry in this implementation.
        except (OSError, ValueError, KeyError, IndexError):
            raise ModelError("api_transport_or_response_error") from None
```

### 15.7 The underlying view, edit, test, and submit tools

`FaultWorkspace` inherits these tools and their source storage. During viewing
and editing, `solution.py` is the name used for the string `self.source`.

Source: [aci_patch_agent/tools.py](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/tools.py#L8), lines 8–68.

<!-- clamp-source: .venv/lib/python3.12/site-packages/aci_patch_agent/tools.py:8:68 -->
```python
# Construct the JSON schema that tells the model how to call each tool.
def tool(name, description, properties=None, required=None):
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties or {},
                           "required": required or [], "additionalProperties": False}}}


TOOLS = [
    # view takes optional start/end line numbers.
    tool("view", "Show numbered lines of solution.py.",
         {"start": {"type": "integer"}, "end": {"type": "integer"}}),
    # edit takes an inclusive line range and replacement code.
    tool("edit", "Replace an inclusive line range. Invalid Python syntax is rejected without changing the source.",
         {"start": {"type": "integer"}, "end": {"type": "integer"}, "replacement": {"type": "string"}},
         ["start", "end", "replacement"]),
    # test runs examples; submit finishes the conversation for final grading.
    tool("test", "Run example checks in an isolated container. Passing examples is not final success."),
    tool("submit", "Finish and submit the current source for separate evaluation."),
]


# This helper supports checked/unchecked editors in the sibling experiment.
# The recovery command uses the default TOOLS and checked=True.
def tool_schemas(checked=True):
    schemas = deepcopy(TOOLS)
    if not checked:
        schemas[1]["function"]["description"] = "Replace an inclusive line range. Syntax is not checked; use test to check behavior."
    return schemas


class Workspace:
    # Both recovery modes keep syntax checking enabled by default.
    def __init__(self, task: Task, sandbox, *, checked=True):
        self.task, self.sandbox = task, sandbox
        # Start with a fresh copy of the broken source string.
        self.source = task.source
        self.checked = checked

    def execute(self, name, args):
        # Arguments must be a JSON object.
        if not isinstance(args, dict):
            return {"error": "Arguments must be a JSON object."}
        # Restrict calls to these tool names and argument names.
        allowed = {"view": {"start", "end"}, "edit": {"start", "end", "replacement"}, "test": set(), "submit": set()}
        if name not in allowed or args.keys() - allowed[name]:
            return {"error": "Unknown tool or argument. Use view, edit, test, or submit."}
        if name in {"view", "edit"}:
            # Use the CURRENT source, including any accepted edits.
            lines = self.source.splitlines()
            # Missing start/end means all current lines.
            start, end = args.get("start", 1), args.get("end", len(lines))
            # Validate inclusive line bounds; the original clamp has only two lines.
            if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
                return {"error": f"Invalid inclusive line range; source has {len(lines)} lines. Source unchanged."}
            # Return requested numbered lines plus total source line count.
            if name == "view":
                # At most 100 lines are returned by an ordinary view.
                end = min(end, start + 99)
                return {"source": "\n".join(f"{i}: {lines[i-1]}" for i in range(start, end + 1)), "total_lines": len(lines)}
            if not {"start", "end", "replacement"} <= args.keys() or not isinstance(args["replacement"], str):
                return {"error": "edit needs start, end, and string replacement. Source unchanged."}
            # Form a candidate by replacing the specified line range.
            candidate = "\n".join(lines[:start-1] + args["replacement"].splitlines() + lines[end:]) + "\n"
            # Reject source larger than 16 KiB.
            if len(candidate.encode()) > 16_384:
                return {"error": "Source exceeds 16 KiB. Source unchanged."}
            # Check syntax in both feedback modes.
            if self.checked:
                try:
                    # compile checks syntax; it does not execute clamp or validate its behavior.
                    compile(candidate, "solution.py", "exec")
                except (SyntaxError, ValueError) as error:
                    # A rejected edit does not update the current source.
                    return {"accepted": False, "error": f"{type(error).__name__}: {error}. Source unchanged."}
            if not candidate.strip():
                return {"error": "Empty source is not accepted. Source unchanged."}
            # Only an accepted candidate replaces self.source.
            self.source = candidate
            # Return updated code through self.execute("view", {}).
            # This calls the override again because self is a FaultWorkspace.
            return {"accepted": True, **self.execute("view", {})}
        # Normal test calls the sandbox with final=False.
        if name == "test":
            return self.sandbox.check(self.task, self.source)
        # After the earlier validation, the remaining valid tool is submit.
        # The loop consumes this result, exits, and runs final grading.
        return {"submitted": True}
```

### 15.8 Inject the timeout: what differs between terse and actionable

This is the full fault override. Its timeout branch is the branch used by both
attempts in the exact command. The annotations also identify the truncation
branch, which that command does not activate.

Source: [agent_recovery_lab/faults.py](agent_recovery_lab/faults.py#L1), lines 1–46.

<!-- clamp-source: agent_recovery_lab/faults.py:1:46 -->
```python
from collections.abc import Callable
from typing import cast

from aci_patch_agent.tasks import Task
from aci_patch_agent.tools import Workspace

from .contracts import FaultKind, JSONValue, Sandbox, ToolObservation


# Inherit the original Workspace tools shown above.
class FaultWorkspace(Workspace):
    # Declare inherited storage and fault state explicitly for the type checker.
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
        # Initialize broken source, sandbox reference, and checked=True.
        super().__init__(task, sandbox)
        # fault="test-timeout" in both attempts; actionable is their only feedback difference.
        self.fault, self.actionable = fault, actionable
        # Each attempt begins with no injected fault.
        self.exposed = False

    def execute(self, name: str, args: JSONValue) -> ToolObservation:
        # Match the FIRST test call whose arguments are exactly {}.
        if self.fault == "test-timeout" and name == "test" and args == {} and not self.exposed:
            # Mark this attempt's fault as already injected.
            self.exposed = True
            # Both modes get this fabricated result. No tests have run.
            result: ToolObservation = {"error": "test_timeout", "passed": False}
            # Terse skips these two added fields; actionable includes them.
            if self.actionable:
                # Explain that no test ran and the source did not change.
                # Suggest a retry. This hint does not execute a retry.
                result.update({"state": "No tests ran. Source unchanged.",
                               "next_action": "This transient timeout happened once. Retry test with empty arguments."})
            # Return immediately, before any sandbox call. There is no actual timeout wait.
            return result
        # All other calls use the original tools.
        # A later test reaches the sandbox because exposed is now True.
        # Describe the inherited tool contract at the untyped dependency boundary.
        execute_base = cast(Callable[[str, JSONValue], ToolObservation], super().execute)
        result = execute_base(name, args)
        # False for this command because clamp has fault="test-timeout".
        # The following branch is for tasks assigned "truncated-view".
        if self.fault == "truncated-view" and name == "view" and "source" in result and not self.exposed:
            # Inspect the ordinary view response, not the stored source.
            lines = result["source"].splitlines()
            # Only responses with multiple source lines can consume this fault.
            if len(lines) > 1:
                self.exposed = True
                # Keep one line in the RESPONSE. Leave self.source intact.
                result["source"] = lines[0]
                result["truncated"] = True
                # Add recovery guidance only in actionable mode.
                if self.actionable:
                    first = int(lines[0].split(":", 1)[0])
                    result["next_action"] = f"Output was truncated, not the file. Use view with start={first + 1}, end={result['total_lines']} to read the remaining lines."
        # Return the observation to the agent loop.
        return result
```

### 15.9 Both clamp modes: complete recorded tool flows

These annotated replays show every executed tool call in
[the September 28 terse clamp attempt](results/week3-pilot/clamp--terse--1.json)
and [the September 28 actionable clamp attempt](results/week3-pilot/clamp--actionable--1.json).
They illustrate the implementations above. They are historical records, not
promised actions or scores for a fresh model run.

`workspace.execute(...)` shows the tool and arguments the model actually chose.
The returned observations are shown as comments directly beside each call.
JSON booleans and null use Python spelling (`True`, `False`, `None`).
The driver does not hardcode either sequence.

**Recorded terse attempt.**

```python
# clamp_task is the selected Task; sandbox is the DockerSandbox from main().
# Construct a fresh workspace for this independent attempt.
workspace = FaultWorkspace(clamp_task, sandbox, fault="test-timeout", actionable=False)

# Action 1: Ordinary range error: the model requests 10 lines, but only 2 exist.
workspace.execute("view", {'start': 1, 'end': 10})
# Returned observation:
# {'error': 'Invalid inclusive line range; source has 2 lines. Source unchanged.'}

# Action 2: The corrected range returns both lines of the broken code.
workspace.execute("view", {'start': 1, 'end': 2})
# Returned observation:
# {'source': '1: def clamp(value, low, high):\n2:     return min(value, high)', 'total_lines': 2}

# Action 3: Install the model-written repair after syntax checking; return the updated source.
workspace.execute("edit", {'start': 1,
 'end': 2,
 'replacement': 'def clamp(value, low, high):\n'
                '    if low > high:\n'
                '        raise ValueError("low cannot be greater than high")\n'
                '    return max(low, min(value, high))'})
# Returned observation:
# {'accepted': True,
#  'source': '1: def clamp(value, low, high):\n'
#            '2:     if low > high:\n'
#            '3:         raise ValueError("low cannot be greater than high")\n'
#            '4:     return max(low, min(value, high))',
#  'total_lines': 4}

# Action 4: Inject the fake timeout. NO example checks run.
workspace.execute("test", {})
# Returned observation:
# {'error': 'test_timeout', 'passed': False}

# Action 5: The terse model submits WITHOUT retrying the timeout.
workspace.execute("submit", {})
# Returned observation:
# {'submitted': True}

# submitted=True causes the loop to exit. Final grading bypasses the fault wrapper.
evaluation = sandbox.check(clamp_task, workspace.source, final=True)
# Recorded final evaluation:
# {'passed': True, 'checks': 6, 'failures': [], 'error': None}
# Recorded actions=5, passed=True, fault_exposed=True.
# failed_actions=2, repeated_actions=0.
# Both failed actions are accounted for: the invalid view and the fake timeout.
```

**Recorded actionable attempt.**

```python
# clamp_task is the selected Task; sandbox is the DockerSandbox from main().
# Construct a fresh workspace for this independent attempt.
workspace = FaultWorkspace(clamp_task, sandbox, fault="test-timeout", actionable=True)

# Action 1: Ordinary range error: the model requests 10 lines, but only 2 exist.
workspace.execute("view", {'start': 1, 'end': 10})
# Returned observation:
# {'error': 'Invalid inclusive line range; source has 2 lines. Source unchanged.'}

# Action 2: The corrected range returns both lines of the broken code.
workspace.execute("view", {'start': 1, 'end': 2})
# Returned observation:
# {'source': '1: def clamp(value, low, high):\n2:     return min(value, high)', 'total_lines': 2}

# Action 3: Install the model-written repair after syntax checking; return the updated source.
workspace.execute("edit", {'start': 1,
 'end': 2,
 'replacement': 'def clamp(value, low, high):\n'
                '    if low > high:\n'
                '        raise ValueError("low cannot be greater than high")\n'
                '    return max(low, min(value, high))'})
# Returned observation:
# {'accepted': True,
#  'source': '1: def clamp(value, low, high):\n'
#            '2:     if low > high:\n'
#            '3:         raise ValueError("low cannot be greater than high")\n'
#            '4:     return max(low, min(value, high))',
#  'total_lines': 4}

# Action 4: Inject the fake timeout. NO example checks run.
workspace.execute("test", {})
# Returned observation:
# {'error': 'test_timeout',
#  'passed': False,
#  'state': 'No tests ran. Source unchanged.',
#  'next_action': 'This transient timeout happened once. Retry test with empty arguments.'}

# Action 5: The model retries. exposed=True now allows the 2 real example checks to run.
workspace.execute("test", {})
# Returned observation:
# {'passed': True, 'checks': 2, 'failures': [], 'error': None}

# Action 6: The actionable model submits after seeing the examples pass.
workspace.execute("submit", {})
# Returned observation:
# {'submitted': True}

# submitted=True causes the loop to exit. Final grading bypasses the fault wrapper.
evaluation = sandbox.check(clamp_task, workspace.source, final=True)
# Recorded final evaluation:
# {'passed': True, 'checks': 6, 'failures': [], 'error': None}
# Recorded actions=6, passed=True, fault_exposed=True.
# failed_actions=2, repeated_actions=0.
# Both failed actions are accounted for: the invalid view and the fake timeout.
```

The terse attempt passed because independent final grading ran its submitted
repair, even though it did not retry `test`. The actionable attempt retried before
submitting. The feedback mode controls the returned information; the model
chooses its next action.

Both recorded attempts submitted this repair:

```python
def clamp(value, low, high):
    # Reject invalid bounds as required by the issue.
    if low > high:
        raise ValueError("low cannot be greater than high")
    # Cap at high, then lift to low if the result is too small.
    return max(low, min(value, high))
```

### 15.10 Run the real checks and grade the code

The injected first timeout returns before this method. A later ordinary `test`
calls `check(..., final=False)`. After the agent loop ends, the direct
`final=True` call runs all six clamp cases.

The driver is the Python program generated below. It loads the current code
inside Docker and returns actual values or exception names to the host grader.

Source: [aci_patch_agent/sandbox.py](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/sandbox.py#L30), lines 30–70.

<!-- clamp-source: .venv/lib/python3.12/site-packages/aci_patch_agent/sandbox.py:30:70 -->
```python
    def check(self, task, source, *, final=False):
        # Ordinary test uses 2 examples. Final grading uses those 2 plus 4 evaluation cases.
        cases = task.examples + task.evaluation if final else task.examples
        # Only inputs go into the container. Expected values stay in the host evaluator.
        # Send only input arguments into Docker; expected answers stay on the host.
        inputs = repr([c.args for c in cases])
        # Generate a small Python program to load the current source and call it.
        driver = (
            "import contextlib, io, json, runpy\n"
            "with contextlib.redirect_stdout(io.StringIO()):\n"
            "    namespace = runpy.run_path('/work/solution.py')\n"
            # For clamp, select namespace["clamp"].
            f"    function = namespace[{task.function!r}]\n"
            "results = []\n"
            # Loop over either 2 or 6 input tuples.
            f"for args in {inputs}:\n"
            "    try:\n"
            "        with contextlib.redirect_stdout(io.StringIO()):\n"
            # Call the actual generated function with each tuple of arguments.
            "            actual = function(*args)\n"
            # Record normal return values.
            "        results.append({'value': actual, 'exception': None})\n"
            "    except Exception as error:\n"
            # Record exception class names for calls that raise.
            "        results.append({'exception': type(error).__name__})\n"
            # Emit JSON results for the host grader.
            "print(json.dumps(results, allow_nan=False))\n"
        )
        # Write and execute the source and driver using _execute below.
        output, error = self._execute(source, driver)
        # Any sandbox execution error fails this check.
        if error:
            return {"passed": False, "checks": len(cases), "failures": [], "error": error}
        try:
            values = json.loads(output)
            # Reject a malformed result list or the wrong number of results.
            if not isinstance(values, list) or len(values) != len(cases):
                raise ValueError("wrong result count")
            failures = []
            for index, (case, actual) in enumerate(zip(cases, values), 1):
                if not isinstance(actual, dict):
                    raise ValueError("invalid result")
                # The invalid-bounds case requires the exception name "ValueError".
                if case.raises:
                    ok = actual.get("exception") == case.raises
                else:
                    value = actual.get("value")
                    # Ordinary cases require both matching type and matching value, with no exception.
                    ok = actual.get("exception") is None and type(value) is type(case.expected) and value == case.expected
                if not ok:
                    # Record every failed case with its input, expected result, and actual result.
                    failures.append({"case": index, "input": repr(case.args),
                                     "expected": case.raises or repr(case.expected), "actual": actual})
            # Pass only if no selected case failed.
            return {"passed": not failures, "checks": len(cases), "failures": failures, "error": None}
        # Malformed evaluator output is itself a failure.
        except (ValueError, TypeError):
            return {"passed": False, "checks": len(cases), "failures": [], "error": "invalid_evaluator_output"}
```

Source: [aci_patch_agent/sandbox.py](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/sandbox.py#L72), lines 72–119.

<!-- clamp-source: .venv/lib/python3.12/site-packages/aci_patch_agent/sandbox.py:72:119 -->
```python
    def _execute(self, source, driver):
        # Give this invocation a unique container name.
        name = f"aci-patch-{uuid.uuid4().hex}"
        # Each invocation gets a separate temporary directory, even when attempts overlap.
        with tempfile.TemporaryDirectory(prefix="aci-patch-") as directory:
            root = Path(directory)
            root.chmod(0o755)
            # Write the in-memory source to a real temporary solution.py.
            (root / "solution.py").write_text(source)
            # Write the generated driver next to the source.
            (root / "driver.py").write_text(driver)
            # Allow the unprivileged container user to read both files.
            (root / "solution.py").chmod(0o644)
            (root / "driver.py").chmod(0o644)
            # Run a disposable container without networking.
            command = ["docker", "run", "--rm", "--name", name, "--network", "none",
                       # Use an unprivileged user and read-only root filesystem.
                       "--user", "65534:65534", "--read-only", "--cap-drop", "ALL",
                       # Limit privileges and process count.
                       "--security-opt", "no-new-privileges", "--pids-limit", "32",
                       # Limit memory/CPU and disable Docker container logging.
                       "--memory", "128m", "--cpus", "1", "--log-driver", "none",
                       # Mount the temporary directory read-only at /work.
                       "-v", f"{root}:/work:ro", "-w", "/work", self.image,
                       # Run the driver in isolated Python without bytecode or site initialization.
                       "python", "-I", "-B", "-S", "/work/driver.py"]
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as stderr:
                process = None
                error = None
                try:
                    # Launch Docker and capture its output.
                    process = subprocess.Popen(command, stdout=output, stderr=stderr)
                    # Set the actual execution deadline, normally 10 seconds.
                    deadline = time.monotonic() + self.timeout
                    while process.poll() is None:
                        # An actual deadline failure is execution_timeout, distinct from the injected test_timeout.
                        if time.monotonic() >= deadline:
                            error = "execution_timeout"
                            break
                        # Also stop on excessive stdout/stderr.
                        if output.tell() + stderr.tell() > 65_536:
                            error = "output_limit"
                            break
                        time.sleep(0.05)
                    # Kill the Docker client on a detected execution limit.
                    if error:
                        process.kill()
                    process.wait(timeout=5)
                    output.seek(0)
                    # Read bounded output for grading.
                    text = output.read(65_537).decode("utf-8", errors="replace")
                    if len(text.encode()) > 65_536:
                        error = "output_limit"
                    # Return output plus any execution error.
                    return text, error or ("execution_error" if process.returncode else None)
                except (OSError, subprocess.TimeoutExpired):
                    return "", "sandbox_error"
                # Clean up even when launching, waiting, or reading fails.
                finally:
                    if process is not None and process.poll() is None:
                        process.kill()
                        process.wait()
                    # Kill the container too: killing the Docker client alone does not stop it.
                    try:
                        # Remove the container too; killing only the client may leave it running.
                        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15)
                    except (OSError, subprocess.TimeoutExpired):
                        # Cleanup failure propagates to the attempt scheduler.
                        raise RuntimeError("Container cleanup failed; check Docker for aci-patch containers.") from None
```

### 15.11 Write the records and build the report

After `run_task` grades and returns, `run_attempt` adds exposure and failure
counts (Section 15.4). `execute_matrix.run` attaches the attempt identity and
writes its JSON (Section 15.3).

This complete report function then reads the saved files. It makes no model
requests and does not rerun the checks.

Source: [aci_patch_agent/experiment.py](https://github.com/altaal/aci-patch-agent/blob/42a2683b643b3b9af2f034529032444accf0c849/aci_patch_agent/experiment.py#L45), lines 45–87.

<!-- clamp-source: .venv/lib/python3.12/site-packages/aci_patch_agent/experiment.py:45:87 -->
```python
def summarize_matrix(output):
    output = Path(output)
    # Use the manifest as the declared denominator.
    manifest = json.loads((output / "manifest.json").read_text())
    rows = []
    # Exactly two entries for this command.
    for attempt in manifest["attempts"]:
        path = output / f"{attempt['id']}.json"
        # A missing file becomes a failed missing_attempt record rather than disappearing.
        result = json.loads(path.read_text()) if path.exists() else {**attempt, "passed": False, "status": "missing_attempt"}
        rows.append(result)
    # Select the CSV columns.
    fields = ["id", "task", "condition", "repeat", "passed", "status", "actions", "model_calls",
              "prompt_tokens", "completion_tokens", "reported_cost_usd", "fault_exposed", "failed_actions", "repeated_actions"]
    with (output / "results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fields, extrasaction="ignore", lineterminator="\n")
        # Write the header, then one row per attempt.
        writer.writeheader()
        writer.writerows(rows)
    summary = {}
    lines = ["# Experiment results", "", "| Condition | Passed / attempts | Rate | Mean actions | Fault exposed |", "| --- | ---: | ---: | ---: | ---: |"]
    # Group separately by terse and actionable.
    for condition in manifest["conditions"]:
        # Each group contains ONE declared attempt here.
        group = [r for r in rows if r["condition"] == condition]
        # Count passes requiring submission and successful final grading.
        passed = sum(bool(r["passed"]) for r in group)
        # Count fault exposure separately.
        exposed = sum(bool(r.get("fault_exposed")) for r in group)
        action_rows = [r["actions"] for r in group if "actions" in r]
        # One attempt per group means its pass rate is either 0.0 or 1.0.
        summary[condition] = {"passed": passed, "attempts": len(group), "pass_rate": passed / len(group),
                              "mean_actions": statistics.mean(action_rows) if action_rows else None,
                              "actions_observed": len(action_rows), "fault_exposed": exposed,
                              # Separately count passes among attempts that encountered the fault.
                              "passed_when_exposed": sum(bool(r["passed"]) for r in group if r.get("fault_exposed")),
                              # Include the failed/repeated action counts from the recovery wrapper.
                              "failed_actions": sum(r.get("failed_actions", 0) for r in group),
                              "repeated_actions": sum(r.get("repeated_actions", 0) for r in group)}
        mean = summary[condition]["mean_actions"]
        # Add the human-readable score row.
        lines.append(f"| {condition} | {passed}/{len(group)} | {100*passed/len(group):.1f}% | {mean if mean is not None else 'N/A'} | {exposed} |")
    lines += ["", "Missing attempts and runner/API errors count as failures. Mean actions uses recorded attempts only.",
              "Repeated runs on the same tasks are not independent task samples; these are descriptive results.",
              "", "## Per-task results", "", "| Task | " + " | ".join(manifest["conditions"]) + " |",
              "| --- | " + " | ".join("---:" for _ in manifest["conditions"]) + " |"]
    # The per-task table has only clamp for this command.
    for task in dict.fromkeys(a["task"] for a in manifest["attempts"]):
        cells = []
        for condition in manifest["conditions"]:
            group = [r for r in rows if r["task"] == task and r["condition"] == condition]
            cells.append(f"{sum(bool(r['passed']) for r in group)}/{len(group)}")
        lines.append(f"| {task} | " + " | ".join(cells) + " |")
    # Write the machine-readable aggregate.
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    text = "\n".join(lines) + "\n"
    # Write the readable Markdown report.
    (output / "summary.md").write_text(text)
    # Return the report to execute_matrix and then main(), which prints it.
    return text
```

```text
runs/pilot-new/
├── manifest.json                # Two declared attempts and their settings.
├── clamp--terse--1.json          # Terse calls, observations, code, grading, usage.
├── clamp--actionable--1.json     # Independent actionable attempt.
├── results.csv                  # Two attempt rows.
├── summary.json                 # Per-mode aggregate counts.
└── summary.md                   # Readable scores and clamp comparison.
```

This is the file set when setup and report writing complete. A new run supplies
its own pass/fail values, code edits, action counts, model responses, and timing.
The historical five-action and six-action examples do not fix those future values.

### 15.12 What truncated-view would do to the same clamp source

This separate illustration answers the earlier comparison between the two fault
types. The command above always selects `FAULTS["clamp"] == "test-timeout"`;
it has no option to assign truncated-view to clamp.

The snippet below explicitly constructs that other fault for illustration.
It calls only `view`. Constructing the `DockerSandbox` configuration below
does not start Docker; a `test` call would execute through that sandbox.

```python
# Separate illustration: these statements are NOT executed by the CLI command above.
# Construct a correctly typed sandbox object; these view calls do not execute it.
sandbox = DockerSandbox()
clamp_task = next(task for task in EVAL_TASKS if task.id == "clamp")

# Same broken clamp code, but a truncated response and terse feedback.
terse = FaultWorkspace(
    clamp_task, sandbox=sandbox, fault="truncated-view", actionable=False
)
first_terse = terse.execute("view", {"start": 1, "end": 2})
# {
#     "source": "1: def clamp(value, low, high):",
#     "total_lines": 2,
#     "truncated": True,
# }
# Only this RESPONSE lost line 2. The stored source still has both lines.

# Another fresh copy of clamp: same truncation, plus actionable guidance.
actionable = FaultWorkspace(
    clamp_task, sandbox=sandbox, fault="truncated-view", actionable=True
)
first_actionable = actionable.execute("view", {"start": 1, "end": 2})
# Same three fields, plus:
# "next_action": "Output was truncated, not the file. Use view with start=2, end=2 to read the remaining lines."

# After the one-time fault, both modes can retrieve the missing line.
# These are demonstration calls; a live model would choose its own next call.
terse_rest = terse.execute("view", {"start": 2, "end": 2})
actionable_rest = actionable.execute("view", {"start": 2, "end": 2})
# Each returns:
# {"source": "2:     return min(value, high)", "total_lines": 2}

# Neither reading nor response truncation changes the stored code.
assert terse.source == actionable.source == clamp_task.source
```


## 16. Type contracts and static checking

All functions and methods defined in the recovery package and its tests have
parameter and return annotations. Classes declare their data fields. The callback
passed to the scheduler is a named, typed function.

A `TypedDict` names a dictionary's fields and their value types. A `Protocol`
describes methods an object must provide, so the real sandbox and a test double
can satisfy the same interface. These definitions keep those meanings next to
the code rather than hiding them behind a generic `dict` or `Any`.

Source: [agent_recovery_lab/contracts.py](agent_recovery_lab/contracts.py#L1), lines 1–100.

<!-- clamp-source: agent_recovery_lab/contracts.py:1:100 -->
```python
"""Type contracts for the recovery layer and its pinned agent dependency."""

from typing import Literal, NotRequired, Protocol, TypeAlias, TypedDict

from aci_patch_agent.tasks import Task


# Only these two fault names are valid.
FaultKind: TypeAlias = Literal["test-timeout", "truncated-view"]
# Feedback style is a separate choice from the fault kind.
FeedbackMode: TypeAlias = Literal["terse", "actionable"]
# Recursive JSON data contains scalars, lists, or string-keyed dictionaries.
JSONValue: TypeAlias = (
    str | int | float | bool | None | list["JSONValue"] | dict[str, "JSONValue"]
)
JSONObject: TypeAlias = dict[str, JSONValue]


# One failed behavioral check, as returned by the pinned sandbox.
class CheckFailure(TypedDict):
    case: int
    input: str
    expected: str
    actual: JSONObject


# Both real and fake sandboxes return these four fields.
class CheckResult(TypedDict):
    passed: bool
    checks: int
    failures: list[CheckFailure]
    error: str | None


# Tools return different subsets of these typed fields.
# total=False means keys can be absent; their values still have types.
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


# Malformed calls and API errors can lack normal event fields.
class ToolEvent(TypedDict, total=False):
    """API errors and malformed calls may lack normal tool-event fields."""

    action: int
    response: int
    tool: str | None
    arguments: JSONValue
    observation: ToolObservation
    error: str


# The complete pinned agent result, plus optional recovery fields.
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
    # Recovery measurements are added after the imported agent returns.
    # NotRequired means these keys can be absent from that initial result.
    fault: NotRequired[FaultKind]
    fault_exposed: NotRequired[bool]
    failed_actions: NotRequired[int]
    repeated_actions: NotRequired[int]


# A Protocol describes required methods, without requiring inheritance.
# The Docker implementation and typed test double both provide check().
class Sandbox(Protocol):
    """Real and test sandboxes support the same grading call."""

    # The star makes final a keyword-only boolean, matching the actual call.
    def check(self, task: Task, source: str, *, final: bool = False) -> CheckResult:
        ...


# A real client or test double can provide this same complete() interface.
class ModelClient(Protocol):
    """Only this client operation is required by the imported agent loop."""

    # The agent exchanges JSON-compatible messages and response records.
    def complete(self, messages: list[JSONObject]) -> JSONObject:
        ...
```

The two casts at the pinned dependency boundary describe the verified tool and
agent-result contracts. A `cast` returns the same value; it performs no runtime
validation, conversion, or repair. Runtime tool validation remains in the original
tool implementation.

Install the development checker and run the checks from this project directory:

```sh
python -m pip install ".[dev]"
python -m mypy
python -m unittest discover -s tests -v
```

Mypy runs in strict mode over `agent_recovery_lab` and `tests`. The exception for
untyped calls is limited to `aci_patch_agent`, the pinned dependency. Its source
is followed so imported task definitions remain available, while its own typing
errors are outside this recovery-layer check. CI installs the development extra
and runs the same type checker before the unit tests.

Historical source excerpts and saved model-written repairs above remain literal
records of their versions. Current recovery snippets, including their annotations,
match the files linked beside them.
