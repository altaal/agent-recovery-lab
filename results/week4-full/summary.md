# Experiment results

| Condition | Passed / attempts | Rate | Mean actions | Fault exposed |
| --- | ---: | ---: | ---: | ---: |
| terse | 26/30 | 86.7% | 6.266666666666667 | 28 |
| actionable | 29/30 | 96.7% | 6.3 | 29 |

Missing attempts and runner/API errors count as failures. Mean actions uses recorded attempts only.
Repeated runs on the same tasks are not independent task samples; these are descriptive results.

## Per-task results

| Task | terse | actionable |
| --- | ---: | ---: |
| clamp | 3/3 | 3/3 |
| safe-mean | 2/3 | 2/3 |
| flatten-once | 2/3 | 3/3 |
| count-words | 3/3 | 3/3 |
| rotate-left | 3/3 | 3/3 |
| palindrome | 1/3 | 3/3 |
| parse-pairs | 3/3 | 3/3 |
| running-total | 3/3 | 3/3 |
| strip-suffix | 3/3 | 3/3 |
| transpose | 3/3 | 3/3 |
