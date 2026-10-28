# Feature Specification: Chart review agent

**Feature Branch**: `015-chart-review-agent`

**Created**: 2026-10-28

**Status**: Draft

**Input**: "Chart review agent on Databricks (as described in databricks/agents/chart_review/AGENTS.md): an
LLM agent that reads one synthetic visit's whole record through read-only tools, weighs evidence types
when they disagree, quotes the record for every claim, may abstain, and returns status, evidence,
deciding evidence and why. Scored as agent:chart_review on the 240 review charts with the same README
metrics and code as every other method, compared with the two rule phenotypes, plus LLM judge
agreement; cost printed and capped before running; one trace per visit tagged with the commit; a
simulated agent for tests and dry runs; deployed with the bundle, endpoint off by default, with usage
tracking; registered only after the acceptance test. Synthetic data only."

> Personal learning project; synthetic data only. The agent's answers are LLM output and are labelled
> as such; simulated runs are `sim:chart_review` and never shown as results. Design notes and rules for
> whoever builds it: [`databricks/agents/chart_review/AGENTS.md`](../../databricks/agents/chart_review/AGENTS.md).

## Context

The study asks one question per visit: *healthy, gingivitis, or periodontitis stage 1–4?* Two kinds of
method answer it today. Models that read only the chart note (best: about 91 of 100 correct), and rule
phenotypes that read the whole record in a fixed order (best: *gum measurements first*, about 98 of 100).
The fixed order is the rule phenotypes' weakness: when the part it trusts first is missing or stale, it
can't weigh the others, and it can't say why it decided.

A reviewer reading a chart does weigh the parts: a probing chart from today outranks an exam form copied
forward; a planned scaling and root planing with no completed one says the patient declined, not that the
disease went away. An agent that reads each part through the repo's own rules
([`docs/evidence_rules.md`](../../docs/evidence_rules.md)), weighs them, and cites what it used could match
the best rule phenotype where the record is complete and explain itself where it isn't. Whether it does is
an empirical question; this spec makes it answerable on the same footing as every other method.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Score the agent like every other method (Priority: P1)

As the project owner, I run the agent over the 240 synthetic review charts and see it in the full results
table, scored with the same metrics and code as every other method, so I can tell whether it beats the
rule phenotypes.

**Why this priority**: Without a like-for-like score the agent is a demo, not a method.

**Independent Test**: Run the simulated agent (no endpoint) over the review charts; `agent`-style rows
appear in the results with every phenotyping metric, labelled simulated and kept out of the README.

**Acceptance Scenarios**:

1. **Given** the review charts and a configured endpoint, **When** the agent runs, **Then** every chart has
   a status or *no answer*, and the full results table has an `agent:chart_review` row with every README
   phenotyping metric (correct, incorrectly assigned, incorrectly ruled out, incorrect stage, no answer,
   unsafe errors, sensitivity, specificity, by note difficulty) and a rank among all methods.
2. **Given** the same inputs, **When** the scores are computed in Python and in R, **Then** they agree to
   1e-9.
3. **Given** the simulated agent, **When** it runs, **Then** its rows are named `sim:chart_review`, labelled
   simulated, and never appear in the README or as results.

---

### User Story 2 - Every answer shows its working (Priority: P1)

As the owner, for any chart I see which parts of the record the agent used, what each said, which one
decided, a quote for each, and one sentence of why, so a reviewer can check it in seconds.

**Why this priority**: An answer that can't be checked can't be trusted on real records later.

**Independent Test**: Run on ten charts; every kept answer lists its evidence with quotes that appear
verbatim in that chart's record.

**Acceptance Scenarios**:

1. **Given** an answer, **When** it is checked, **Then** each piece of evidence quotes the record verbatim
   (note text or field value), and the deciding evidence is one of them.
2. **Given** an answer whose quotes don't appear in the record, or that doesn't match the required shape,
   **When** it is checked, **Then** it is counted as *no answer*, not repaired or re-asked silently.
3. **Given** a record that can't support any status, **When** the agent abstains, **Then** the chart counts
   as *no answer*, exactly as for any other method.

---

### User Story 3 - The agent reads the record through the repo's rules (Priority: P2)

As the owner, I want the agent to get what each part of the record says from the same tested rules the
rule phenotypes use, so its value is in weighing evidence, not in re-inventing the rules.

**Why this priority**: Rules restated in a prompt drift from the code and can't be tested.

**Independent Test**: For each evidence type, the tool the agent calls returns exactly what the repo's
reader for that type returns on the same input (the worked examples in `docs/evidence_rules.md`).

**Acceptance Scenarios**:

1. **Given** a visit, **When** the agent asks for its evidence, **Then** it gets every part of that visit's
   record and nothing else; never the answer key.
2. **Given** an evidence type and a value, **When** the agent asks what it says, **Then** the answer matches
   the repo's reader for that type.
3. **Given** any tool, **When** it is called, **Then** it changes no data.

---

### User Story 4 - Cost and traceability (Priority: P2)

As the owner, I see the estimated cost before a run, the run stops if it would exceed a set limit, and
afterwards I can open any chart's full exchange with the model and know which commit produced it.

**Why this priority**: LLM runs cost money and must be reproducible.

**Independent Test**: Start a run with a limit below the estimate; it stops before calling the model and
says why. Start one under the limit; each chart has one trace tagged with the deployed commit.

**Acceptance Scenarios**:

1. **Given** a run, **When** it starts, **Then** it prints the number of calls, estimated tokens and US$ at
   the endpoint's list price, and stops if the estimate exceeds the limit (default US$5).
2. **Given** a completed run, **When** I open the experiment, **Then** each chart has one trace with the
   tool calls, the answer and the quote check, tagged with the deployed commit and labelled LLM output.
3. **Given** a rerun, **When** some charts already have answers from the same endpoint and prompt version,
   **Then** only the missing ones are asked.

---

### User Story 5 - Deploy like everything else, off by default (Priority: P3)

As the owner, the agent's job is deployed with the bundle to every target, does nothing until an endpoint
is set, and is registered as a model only if it passes the same acceptance test as the others.

**Why this priority**: Keeps the agent inside the existing release process.

**Independent Test**: Deploy with the endpoint unset; the job exists and a run reports that the agent is
off without calling anything.

**Acceptance Scenarios**:

1. **Given** the endpoint setting is `none` (the default), **When** the job runs, **Then** it calls no model
   and says so.
2. **Given** a run that fails the acceptance test, **When** registration is attempted, **Then** nothing is
   registered.

### Edge Cases

- A part of the record is missing: the agent sees it as missing (the reader's *unknown*), never as
  healthy.
- The model returns malformed output, times out or errors: the chart counts as *no answer* for that run;
  endpoint errors (not answers) are retried on the next run.
- The model asks for a tool that doesn't exist or loops on tool calls: stopped after a fixed number of
  calls; the chart counts as *no answer*.
- A note fails the leak gate: it is never sent to the model; the chart is skipped and reported.
- Two parts of the record disagree and neither is clearly more trustworthy: the agent may abstain or pick
  one, but must quote both.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001** The agent answers, per visit, one of the six statuses or *no answer*, for the 240 synthetic
  review charts.
- **FR-002** The agent reads a visit only through read-only tools that return (a) the visit's whole record
  (exam form, procedure and diagnosis codes planned and completed, probing chart summary, X-ray reading,
  de-identified note), (b) what the repo's reader for an evidence type says about a value, and (c) the
  plain-words rule for an evidence type. No tool exposes the answer key or writes data.
- **FR-003** Each answer includes: status, the evidence used (type, what it says, a verbatim quote or field
  value), the deciding evidence, and one sentence of why.
- **FR-004** Every quote is checked against the record with the repo's existing quote gate; an answer that
  fails the check, or doesn't match the required shape, counts as *no answer*.
- **FR-005** Only notes that passed de-identification and the leak gate are sent to the model.
- **FR-006** Scores use the same code and metrics as every other phenotyping method; the method is named
  `agent:chart_review` (simulated: `sim:chart_review`) and appears in the full results table and, if it is
  the best of a group, in the README group it belongs to. Python and R agree to 1e-9.
- **FR-007** The results compare it with both rule phenotypes on the same charts, with 95% intervals, and
  report the LLM judge's agreement with its answers, labelled LLM judgment.
- **FR-008** Before calling the model, a run prints the call count, estimated tokens and US$ at the
  endpoint's list price, and stops if the estimate exceeds a set limit (default US$5).
- **FR-009** Each chart's exchange is recorded as one trace in the project's experiment, tagged with the
  deployed commit and labelled LLM output; per-run cost, tokens, latency, errors and quote-check failures
  are reported like the judge's.
- **FR-010** Reruns reuse answers from the same endpoint and prompt version and ask only for the missing
  ones.
- **FR-011** A simulated agent with the same output shape runs without any endpoint, for tests and dry
  runs.
- **FR-012** The job is deployed with the bundle to every target with identical names; the endpoint is a
  per-target setting defaulting to `none` (agent off); usage tracking and a rate limit are on for the
  endpoint where the workspace supports them.
- **FR-013** The agent is registered as a model only after passing the same acceptance test as the other
  models.
- **FR-014** Each run caps tool calls per chart; exceeding it counts as *no answer*.

### Key Entities

- **Visit record**: everything the agent may read for one visit, by evidence type; no answer key.
- **Agent answer**: visit, status or *no answer*, evidence list (type, says, quote), deciding evidence,
  why, quote-check result, prompt version, endpoint, commit, tokens, latency.
- **Agent run**: calls, charts, errors, quote-check failures, tokens, US$, latency; per run.
- **Method row**: `agent:chart_review` in the results, with every phenotyping metric and its rank.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** All 240 review charts get a status or *no answer*, and the agent appears in the full results
  table with every phenotyping metric and a rank.
- **SC-002** 100% of kept answers have every quote found verbatim in the record (answers failing the check
  are counted as *no answer*, and their share is reported).
- **SC-003** A full run over the review charts costs under US$5 at list price, estimated and printed
  before it starts.
- **SC-004** Any chart's answer, evidence and quotes can be opened and checked by a reviewer in under a
  minute.
- **SC-005** The comparison with the best rule phenotype states, with a 95% interval, whether the agent is
  better, no different, or worse on exact status; either outcome is reported.
- **SC-006** With the endpoint unset, a deploy and a job run complete without calling any model.

## Assumptions

- Synthetic data only; the review charts and answer key are the generator's. The agent never sees the key.
- A pay-per-token chat endpoint with tool calling is available in the dev workspace (the judge already uses
  one); the default model is the judge's unless the plan finds a better-suited one.
- The repo's readers and `docs/evidence_rules.md` are the source of each evidence type's rule.
- The existing quote gate, leak gate, scoring code, cost reporting and commit tagging are reused, not
  rebuilt.
- A tool-call cap of 10 per chart is enough for six evidence types plus rule lookups.
- The README's best-per-group summary may gain an agent group only if it beats an existing group's best;
  otherwise it appears in the full table only.

## Out of Scope

- Real records, or any change to the de-identification or leak gate.
- Letting the agent change the rules, the answer key or the rule phenotypes.
- Grading or extent (status only, as for every other method).
- Fine-tuning the model behind the agent.
