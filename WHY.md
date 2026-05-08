# Why open-bench exists

## The problem

Public coding-LLM benchmarks have three specific gaps a buyer hits the
moment they try to use one.

1. **They score one-shot prompts on synthetic problems.** Pass@1 on
   HumanEval or MBPP tells you whether a model can complete a textbook
   exercise. It tells you nothing about how that same model behaves
   inside a multi-turn agent loop where the diff has to be reviewable,
   the wall-clock has to fit a sprint, and the cost has to fit a
   budget.
2. **Judge-bias is rarely surfaced, almost never corrected.**
   Model-as-judge is the standard scoring methodology now. Models
   systematically overrate their own outputs and the outputs of
   models from the same vendor family. Most leaderboards do not
   compute this delta, let alone publish it.
3. **The lineup mixes proprietary and open-weight models.** A buyer
   evaluating open-source coding models for an air-gapped or
   self-hosted deploy gets a confused signal — half the leaderboard
   is unreachable, and the methodology that produced the rankings
   doesn't account for the asymmetry.

## The stance

open-bench commits to three things competitors don't combine.

- **Open-source models only.** The lineup is curated, not exhaustive.
  Proprietary models stay out of the comparison set; the project
  doesn't try to be a universal leaderboard.
- **Round-based, methodology evolves in public.** Each round publishes
  what changed (task selection, judge configuration, scoring rules)
  and why. Static benchmarks decay as models adapt to them; living
  ones update.
- **Judge bias is a first-class column.** Self-bias delta and
  inter-judge agreement are computed and shown every round, not
  buried in an appendix. The bias matrix is part of the result, not
  a footnote.

## What gets measured

Every implementation in every round produces four numbers:

| Column | Source |
|---|---|
| Hidden-test pass rate | `test-output.txt` from each run dir, parsed by `_pytest_parse` |
| Blinded peer scores | every model judges every implementation under random labels; `aggregate_judges` medians them across the expert / peer / self tiers |
| Model wall-clock | sum of agent-loop turn durations from the opencode session export |
| Dollar cost | from each provider's billing dashboard, recorded into `meta.json` after capture |

Hidden tests run *before* any judge sees the code, so a non-functional
implementation cannot be inflated by qualitative scoring. The full
artifact set — transcripts, diffs, judge rubrics, raw scores —
commits alongside the round under `builds/<model>/rounds/` and
`results/judgments/`. Every round is reproducible from the repo: same
prompt, same hidden tests, same scoring math.

## What this isn't

- **It won't rank closed models.** By design. If the question is "GPT-5
  vs Claude vs Gemini," look at Chatbot Arena or Vellum.
- **It won't predict your specific codebase's results.** Task selection
  biases everything. The tasks are public and the rationale for each
  is documented; if the task mix doesn't match your work, the rankings
  won't either.
- **It isn't an eval framework.** `inspect_ai`, `promptfoo`, and
  `braintrust` exist for that. open-bench is a benchmark with one
  opinionated methodology, not a substrate for arbitrary evals. The
  `_kinds/` registry is internal — not a public plugin API today.

## What's next

Round 2 introduces a different scoring modality (reddit user-vote
experiment over the same lineup), keeping the methodology living.
The harness is `pip install`-able, the engine is provider-agnostic
(opencode is one swappable driver), and `CONTRIBUTING.md` documents
the path to add a task in 30 minutes. Rough monthly cadence going
forward; if the methodology compounds across three rounds of data,
a paper follows.

The harness, the rounds, and the methodology all sit in
[github.com/anfocic/open-bench](https://github.com/anfocic/open-bench).
