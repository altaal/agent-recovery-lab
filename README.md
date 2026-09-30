# Agent Recovery Lab

Does explaining a tool failure help the same coding agent finish its task?

This repository runs the [ACI Patch Agent](https://github.com/altaal/aci-patch-agent)
at a pinned commit. It owns the controlled faults and comparison, not a second
agent implementation. All scenarios use the same model, tools, tasks, and limits.

This repository covers Weeks 3–4 of the
[shared six-week plan](https://github.com/altaal/aci-patch-agent/blob/main/WEEK_BY_WEEK.md).
In the sibling-project workspace, its canonical editable source is `../WEEK_BY_WEEK.md`.

## Run

Requires Python 3.11+, Docker, and `OPENROUTER_API_KEY` set in the environment.
Live experiments make paid OpenRouter calls; reporting makes none.

```sh
git clone https://github.com/altaal/agent-recovery-lab.git
cd agent-recovery-lab
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
docker pull python@sha256:da047cb8f9d1d98e5c070f5300ba9f7274e33b8fc0e5be5ed88740aed1b95ba9
python -m agent_recovery_lab.run --pilot --output runs/pilot
```

The pilot is five scenarios, two conditions, one attempt per condition. The full
experiment is ten scenarios, two conditions, three attempts per condition:

```sh
python -m agent_recovery_lab.run --output runs/full
```

Output directories must be new. The runner never replaces earlier attempts.

## What changes, and what stays fixed

Five scenarios inject one synthetic timeout on the first `test` call. The call
returns without running any tests. The next call works normally. Five scenarios
truncate the first multi-line `view` response to one line. The underlying source
stays intact and a later `view` can retrieve it. Source is not supplied in the
initial prompt in either condition, so the agent must use the viewing tool.

| Condition | Example timeout response |
| --- | --- |
| terse | `test_timeout` |
| actionable | The same error, plus: no tests ran; source is unchanged; retry `test`. |

For truncated output, both conditions receive the same first line, total line
count, and truncation flag. Only the actionable condition receives a suggested
range for the next `view`. Neither condition receives a correct patch or final
evaluation answer.

The model is `qwen/qwen3-next-80b-a3b-instruct`, temperature 0. Each attempt has at
most 15 actions, 1,200 completion tokens per call, and the same reported-token
stopping threshold. Calls can still vary because of model/provider behavior.
Results are descriptive; three attempts on a task are not three independent tasks.

## How to read the results

A pass requires submission and passing every final behavioral check. A fault is
**exposed** only if the relevant tool was actually called and its fault injected.
A pass without exposure is not evidence of recovery. The CSV records exposure
per attempt, and the JSON summary separately counts passes among exposed attempts.

`failed_actions` counts error responses, rejected edits, and failed example checks.
`repeated_actions` counts failed calls with the same tool and arguments as an earlier
failed call. It does not count all no-op edits or classify the model's reasoning.

Each attempt saves the live messages, tool observations, source, patch, score,
token usage, and stopping status. Missing attempts and runner errors count as
failures in the declared denominator. The manifest records the full attempt list,
code hashes, task hash, and pinned agent revision before execution.

## Check

```sh
python -m unittest discover -s tests -v
```

Tests verify one-time fault injection, unchanged source, retrievable truncated
lines, and exposure accounting. They use no model key. The underlying agent's
container and scoring tests run in its own repository.

## Measured results

The five-scenario pilot passed 5/5 attempts in each condition. Every attempt
encountered its fault. [Pilot traces and table](results/week3-pilot/).

The full experiment used ten scenarios and three repetitions, September 28, 2026:

| Feedback | All declared attempts | Encountered fault | Passed among exposed | Mean actions |
| --- | ---: | ---: | ---: | ---: |
| Terse | 26/30 (86.7%) | 28 | 26/28 (92.9%) | 6.27 |
| Actionable | 29/30 (96.7%) | 29 | 29/29 (100%) | 6.30 |

[Full per-task table](results/week4-full/summary.md),
[CSV](results/week4-full/results.csv), [all traces](results/week4-full/),
and [what failed / what I learned](FAILURES.md).

Two terse palindrome attempts produced correct code but repeatedly edited it
instead of submitting. Three other attempts stopped on API transport/response
errors before fault exposure; those remain failures in the headline denominator.
The saved error does not identify the underlying network/provider cause.

The clearer feedback did better on this small suite, but was not faster and did
not reduce the recorded failed-action count. Do not generalize a difference on ten
authored tasks into a reliability guarantee. See the
[plain-language six-week guide](https://github.com/altaal/aci-patch-agent/blob/main/WEEK_BY_WEEK.md)
for how this experiment connects to the other artifacts.

Regenerate either published table without a model key:

```sh
python -m agent_recovery_lab.run --report-only --output results/week3-pilot
python -m agent_recovery_lab.run --report-only --output results/week4-full
```

Out of scope: new agent architecture, production incident simulation, parallel
agents, arbitrary repositories, model training, and claims about security behavior.
