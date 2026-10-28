# Feature Specification: Databricks AI features in the AI-use review and the evaluation

**Feature Branch**: `017-databricks-ai-functions` (work lands on the session branch `claude/great-cerf-qwbqck`)

**Created**: 2026-10-28

**Status**: implemented; first runs need the owner's approval (they bill the workspace)

**Input**: "The Databricks internal AI methods are not in the AI use review or evaluation."

> Personal learning project; synthetic data only. The functions receive only the 240 de-identified,
> leak-gated synthetic review notes, the same text the MedGemma reader and the LLM judge read.

## User stories

### US1 - Every Databricks AI feature is in the model inventory (P1) #86
`docs/model_inventory.md` gets a Databricks section. For each feature it gives what it does here, the
model behind it (or that Databricks doesn't name one), what text it receives, its status, and its
documentation link. The features are:
- AI Functions: `ai_query`, `ai_classify`, `ai_extract` and `ai_mask`.
- Foundation Model API endpoints.
- MLflow judges: `make_judge` and the built-in Guidelines judge.
- Production monitoring scorers, AI Gateway, Genie and the Databricks Assistant.

A test fails if the code calls an AI Function the inventory doesn't list.

### US2 - `ai_classify` is a phenotyping method (P1) #87
`ai_classify` (version 2.1) labels each review note with one of the six statuses, each label carrying a
one-line description from the same AAP/EFP criteria the reader prompt uses.
- Output: `ai_predictions_dbai-classify.csv`, scored by the existing code like every other method.
- It is LLM output, grouped with the LLM readers, and its plain name is "Databricks ai_classify".
- A note it can't classify (NULL or an error) is *no answer*, never a guess.

### US3 - `ai_query` on a pay-per-token model is a zero-shot note reader (P2) #88
The MedGemma reader's prompt (`reader-v2`) and answer parsing (quote gate) run through `ai_query` on a
Databricks Foundation Model endpoint. The endpoint is a setting, defaulting to the judge's
`databricks-meta-llama-3-3-70b-instruct`.
- Output: `ai_predictions_dbai-query-<endpoint>.csv` and `llm_details_dbai-query-<endpoint>.csv`, so Load
  results also puts them in the gold tables.

## Rules for both methods
- **Configuration checked first:** `DATABRICKS_HOST`, `DATABRICKS_TOKEN` and `DATABRICKS_WAREHOUSE_ID`.
  The warehouse must be serverless, because `ai_classify` v2 isn't available on Pro or Classic.
- **Cost shown before running:** the call count and token estimate are printed. `--max-notes` caps a
  run, and `--limit` makes it a test.
- **Results are real or simulated, never mixed:** a dry run (`--simulate`) writes `simulated_*` files
  only.
- **Reruns overwrite** that method's files (idempotent). Calls go in batches; one failed batch is
  retried once, then its notes are *no answer*.

## Out of scope
- `ai_extract` as a measurement reader (extract CAL/PD, then the rule): listed in the inventory, not
  evaluated.
- Genie and the Assistant: they aren't pipeline methods. They're listed because people use them in the
  workspace.

## Success criteria
- `pytest` covers statement building, response parsing (v2 VARIANT, v1 string, NULL, error), simulated
  runs and naming.
- After approval, both methods appear in the full results table with real scores.
