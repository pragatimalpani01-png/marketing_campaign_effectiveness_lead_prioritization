# Experiment plan: separate a better story from a better result

The dashboard can help pick a place to investigate. It cannot tell whether moving budget or changing sales response will cause better results. The next step should be a small test with a clear comparison group.

## Test 1: Does a faster handoff improve conversion?

**Question:** For leads with a demo request or repeated pricing activity, does a faster sales response increase sales acceptance and eventual wins?

**Design:** Randomly assign eligible new leads within channel and company-size band to either the existing response process or a defined fast-response process. Do not let reps choose which group gets the faster follow-up. Use the same qualification rules in both groups.

**Primary measure:** Sales acceptance within seven days of the trigger event.

**Later measures:** Win rate within a fixed follow-up window, time to first response, booked value, and the share of leads with no logged next step.

**Guardrails:** Unsubscribe or complaint rate, duplicate contact rate, rep workload, and whether one group receives materially different offers or discounts.

**Before launch:** Use the actual CRM baseline to calculate the sample size needed to detect a meaningful change. Do not stop the test early because the first week looks encouraging. Keep the assignment and analysis rules written down before the first lead is randomized.

## Test 2: Can budget shift without giving up useful demand?

**Question:** Does a small increase in one campaign create incremental sales-accepted leads and wins, or merely reach people who would have converted anyway?

**Design:** Choose one source and one destination from the dashboard sandbox. Move a limited amount of budget, keep a matched control where the channel and platform allow it, and avoid changing landing pages, audience, offer and follow-up at the same time. Where platform-level randomization is unavailable, consider a matched market or staggered rollout, with the limitations documented.

**Primary measure:** Incremental cost per sales-accepted lead or incremental wins, not leads alone.

**Secondary measures:** Spend, cost per win, booked value, lead quality, sales cycle and unsubscribe/complaint rate.

**Guardrails:** Total spend, qualified pipeline, frequency, audience overlap and sales capacity. Set the minimum acceptable outcome before launching.

## How to read the result

Report the difference between the test and comparison groups, uncertainty around that difference, and any changes in delivery or sales handling. If the sample is too small to distinguish a useful effect from noise, keep the result inconclusive. Do not use the historical revenue-to-spend ratio as a substitute for the experiment.

The current repository has no randomized data. This plan describes a next step for a real campaign, not a result from the synthetic sample.
