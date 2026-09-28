# What failed / what I learned

All 70 pilot and full-experiment attempts are retained. A pass means the agent
submitted and the independent final checks passed. The pilot and full experiment
are reported separately; they are not pooled into a larger score.

## 1. Correct code can still be an unfinished agent task

Full-run palindrome with terse feedback, [attempt 1](results/week4-full/palindrome--terse--1.json)
and [attempt 3](results/week4-full/palindrome--terse--3.json), both encountered the
truncated view and produced a correct fix at action 3. The examples passed at
action 4. The model then repeated a view/edit/test pattern instead of submitting.
Both stopped at 15 actions. The final six checks passed, but neither agent run did.

All three actionable palindrome attempts submitted and passed. This is an observed
association on one task, not proof that a hint always prevents a stall. Keep
completion as a separate requirement from code correctness.

## 2. Infrastructure errors belong in the record

[Safe mean, terse](results/week4-full/safe-mean--terse--1.json),
[safe mean, actionable](results/week4-full/safe-mean--actionable--1.json), and
[flatten once, terse](results/week4-full/flatten-once--terse--1.json) stopped on
`api_transport_or_response_error`. The saved message groups transport and response
parsing failures; it cannot establish a specific root cause such as rate limiting.

None of these attempts reached the injected fault. One already had correct code
when the API failed, but still never submitted. All three count as failed attempts.
The secondary exposed-fault rates are 26/28 versus 29/29; they explain what was
actually exercised and do not replace the headline 26/30 versus 29/30.

## 3. More successful runs did not mean fewer actions

The actionable condition averaged 6.30 actions, versus 6.27 for terse. It recorded
46 failed actions and two repeated failed calls; terse recorded 40 and zero.
These counters include the deliberately injected timeouts and ordinary invalid
line ranges. They do not count accepted no-op edits, so they miss the palindrome
stalls described above. Do not label them a complete measure of wasted work.

The five-scenario pilot passed in both conditions, showing a ceiling on that tiny
sample. Expanding to ten fixed tasks exposed the termination failures. Retain
per-task traces and multiple measurements rather than selecting one favorable metric.

## Boundaries

These are synthetic, single-event faults in tiny Python tasks. Both conditions
share the same source, model, action limit, and evaluator. They receive identical
error/data content except for an actionable state explanation and retry hint.
The source is hidden initially in both conditions. Public tasks, provider routing,
and only ten independent task definitions limit any broader conclusion.
