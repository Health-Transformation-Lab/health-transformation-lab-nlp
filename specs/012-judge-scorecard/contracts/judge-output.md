# Contract: judge output (prompt `judge-v3`)

Both calls answer with JSON only. Anything else is parsed as a failed gate.

## Status call (no answer shown)

```json
{"supported_status": "healthy" | "gingivitis" | "periodontitis_stage_1" | "periodontitis_stage_2"
                     | "periodontitis_stage_3" | "periodontitis_stage_4" | null,
 "quote": "exact text from the note that decides it",
 "rationale": "one sentence"}
```

Gate: `supported_status` is one of the six or null; when not null, `quote` is non-empty and
appears verbatim in the note.

## Verdict call (answer shown)

Unchanged from `judge-v2` (`judge.SYSTEM`):

```json
{"verdict": "correct" | "incorrect" | "not_determinable",
 "supported_status": one of the six or null,
 "quote": "...", "rationale": "..."}
```

Gate: `judge.gate` (verdict valid, status valid, quote verbatim unless not determinable).

## Bundle variable

`judge_endpoint`: a serving endpoint name, or `none` to skip the judge. dev default
`databricks-meta-llama-3-3-70b-instruct`.
