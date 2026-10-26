# Outcomes and recommended actions

All results below come from the synthetic dataset bundled with this repository. They illustrate how the analysis works and are not business findings about a real company.

## The headline numbers

| Measure | Sample result |
|---|---:|
| Leads | 7,200 |
| Recorded campaign spend | $760,209 |
| Marketing-qualified leads | 3,002 |
| Sales-accepted leads | 1,602 |
| Won deals | 553 |
| Booked deal value | $8,768,402 |
| Cost per lead | about $106 |
| Cost per won deal | about $1,375 |
| Booked revenue per recorded campaign dollar | 11.53x |

Revenue-to-spend is included because it is easy to understand, but it is not profit. It excludes gross margin, sales costs and other operating costs.

## What stands out

**Partner events look efficient in this sample.** Partner has the highest recorded channel revenue-to-spend ratio, around 21.8x, on 437 leads and 44 wins. That ratio should be read alongside the smaller volume. It is not enough, on its own, to justify moving a large budget into partner activity.

**Paid Search contributes the most booked revenue overall.** It records roughly $2.16 million in booked deal value in the sample. Its revenue-to-spend ratio is lower than Partner and Webinar, but its contribution in total dollars is larger. The best ratio and the biggest revenue contribution answer different questions.

**Paid Social creates the largest lead volume, but has the lowest channel revenue-to-spend ratio in the sample.** The next step is to check campaign mix, account fit and downstream acceptance before making a blanket decision about the whole channel. The three Paid Social campaigns do not perform the same way.

**The score helps sort the queue.** A logistic-regression model trained through September was checked on the following quarter. The top-scoring 10% had a 21.5% observed win rate, compared with about 9.0% across the full holdout. That is roughly 2.39x lift. The model is useful as a ranking example, but its performance needs testing on real, later-dated CRM outcomes before use.

**Attribution changes who gets credit.** About $1.86 million of booked-revenue credit (21.2% of the total) changes channel bucket when the report switches from first-touch to last-touch. A lead may first arrive through organic search, return through email, and finish after a partner event. First-touch, last-touch and linear views allocate that win differently. This is a reason to inspect the journey, not proof that one channel caused the deal.

## What a team could do next

1. Set a clear response-time target for demo requests and repeated pricing-page visits. Measure whether faster follow-up improves sales acceptance and win rate.
2. Review cost per sales-accepted lead and cost per win alongside cost per lead. Use lead volume as context, not as the final score.
3. Review the campaigns within a channel before deciding whether the entire channel deserves less spend. Named-account outreach is expensive per lead in this sample, but has larger average deal value.
4. Use the budget sandbox to form a small test. Keep a comparison group where possible, and look at incremental conversions rather than relying on historical ratios alone.
5. For a live version, add account-level deduplication, margins, sales effort, loss reasons, longer attribution windows and a proper holdout period for model validation.
