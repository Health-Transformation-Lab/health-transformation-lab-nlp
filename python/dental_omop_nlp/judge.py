"""LLM-as-judge for periodontal status predictions.

With a million notes there is no human gold for almost all of them. The judge
reads a de-identified note and one model's predicted status and answers: is
that status supported by the note? It must quote the sentence that decides it,
and the quote must appear verbatim in the note or the verdict is discarded
(the quote gate). Verdicts:

    correct          the note supports the predicted status
    incorrect        the note supports a different status (judge gives which)
    not_determinable the note alone can't settle it

The judge is itself a model and makes mistakes. Before its verdicts are used
to estimate a model's accuracy on the million-note corpus, it is calibrated on
the human-reviewed charts (cost_effectiveness.calibrate_judge) and the
estimates are corrected for its sensitivity and specificity.

Backends
  openai     any OpenAI-compatible chat endpoint. Databricks Model Serving
             endpoints are; set JUDGE_BASE_URL=https://<workspace>/serving-endpoints
             and JUDGE_API_KEY=<token>, JUDGE_MODEL=<endpoint name>.
  simulated  no LLM. Reads the generator's truth and flips verdicts at a set
             error rate so the pipeline can be dry-run. Output is labelled
             simulated everywhere it lands. Never a result.
On Databricks the same prompt runs as SQL through ai_query (databricks/notebooks/02_llm_judge.sql).

Only de-identified notes may be sent to a judge.
"""

from __future__ import annotations

import json
import os
import random
import time
import urllib.request
from dataclasses import dataclass

from .labels import LABELS

PROMPT_VERSION = "judge-v2"   # v2: AAP worksheet rules (CAL first, complexity, grade)

# Status definitions and rules, shared with the note reader (llm_reader.py).
CRITERIA = """Status definitions (AAP staging and grading worksheet, 2017 AAP/EFP):
- healthy: no interdental attachment loss, bleeding on probing (BOP) < 10% of sites
- gingivitis: no interdental attachment loss, BOP >= 10%
- periodontitis_stage_1: interdental CAL 1-2 mm (RBL < 15% if CAL not recorded), no tooth loss due to perio, max probing depth <= 4 mm
- periodontitis_stage_2: CAL 3-4 mm (RBL 15-33% if CAL not recorded), no tooth loss due to perio, max probing depth <= 5 mm
- periodontitis_stage_3: CAL >= 5 mm (RBL beyond the coronal third if CAL not recorded) or 1-4 teeth lost due to perio
- periodontitis_stage_4: stage 3 severity with >= 5 teeth lost due to perio or a need for complex rehabilitation
Rules: the initial stage comes from interdental CAL at the worst site; use radiographic bone \
loss only when CAL is not recorded. Complexity factors raise the stage, never lower it: probing \
depth >= 6 mm, vertical bone loss >= 3 mm or class II/III furcation -> at least stage 3; at stage 3, \
mobility degree >= 2, fewer than 20 remaining teeth, masticatory dysfunction, bite collapse, \
drifting/flaring or a severe ridge defect -> stage 4. Measured findings outrank a written \
diagnosis; ignore text copied forward from previous visits; pre-2017 terms map slight=stage 1, \
moderate=stage 2, severe=stage 3 (4 if >= 5 teeth lost to perio).
Grade (periodontitis only): start at B; use direct evidence of progression over 5 years if \
present (none A, < 2 mm B, >= 2 mm C), else % bone loss / age (< 0.25 A, 0.25-1.0 B, > 1.0 C); \
smoking < 10/day or diabetes with HbA1c < 7.0% -> at least B; >= 10/day or HbA1c >= 7.0% -> C.
Extent: localized < 30% of teeth, generalized >= 30%, or molar/incisor pattern."""

SYSTEM = ("You are a periodontist auditing an automated classifier. You judge whether a dental "
          "chart note supports a predicted periodontal status under the 2017 AAP/EFP classification.\n\n"
          + CRITERIA + """

Answer with JSON only:
{"verdict": "correct" | "incorrect" | "not_determinable",
 "supported_status": one of the six statuses or null,
 "quote": "the exact sentence or phrase from the note that decides it, copied verbatim",
 "rationale": "one sentence"}"""

)

USER = """Note:
<<<
{note}
>>>

Predicted status: {pred}

Is the predicted status supported by the note?"""


@dataclass
class Verdict:
    verdict: str
    supported_status: str | None
    quote: str
    rationale: str
    quote_ok: bool
    input_tokens: int
    output_tokens: int
    latency_s: float
    error: str = ""


def _parse(raw: str) -> dict:
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`").split("\n", 1)[1] if "\n" in s else s
    start, end = s.find("{"), s.rfind("}")
    return json.loads(s[start:end + 1])


def gate(note: str, out: dict) -> tuple[bool, str]:
    """Quote gate plus schema check. Returns (ok, reason)."""
    if out.get("verdict") not in {"correct", "incorrect", "not_determinable"}:
        return False, "bad verdict"
    if out.get("supported_status") not in (None, *LABELS):
        return False, "bad status"
    q = (out.get("quote") or "").strip()
    if out["verdict"] != "not_determinable" and (not q or q not in note):
        return False, "quote not in note"
    return True, ""


class OpenAIJudge:
    def __init__(self, model: str | None = None, base_url: str | None = None, api_key: str | None = None,
                 temperature: float = 0.0, max_retries: int = 3):
        self.model = model or os.environ["JUDGE_MODEL"]
        self.base_url = (base_url or os.environ["JUDGE_BASE_URL"]).rstrip("/")
        self.api_key = api_key or os.environ["JUDGE_API_KEY"]
        self.temperature, self.max_retries = temperature, max_retries

    def __call__(self, note: str, pred: str) -> Verdict:
        body = json.dumps({"model": self.model, "temperature": self.temperature, "max_tokens": 300,
                           "messages": [{"role": "system", "content": SYSTEM},
                                        {"role": "user", "content": USER.format(note=note, pred=pred)}]}).encode()
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body, method="POST",
                                     headers={"Authorization": f"Bearer {self.api_key}",
                                              "Content-Type": "application/json"})
        err = ""
        for attempt in range(self.max_retries):
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    resp = json.loads(r.read())
                usage = resp.get("usage", {})
                out = _parse(resp["choices"][0]["message"]["content"])
                ok, why = gate(note, out)
                return Verdict(out.get("verdict", ""), out.get("supported_status"), out.get("quote", ""),
                               out.get("rationale", ""), ok, usage.get("prompt_tokens", 0),
                               usage.get("completion_tokens", 0), time.time() - t0, why)
            except Exception as e:  # network, rate limit, bad JSON: retry, then record as an error row
                err = f"{type(e).__name__}: {e}"
                time.sleep(2 ** attempt)
        return Verdict("", None, "", "", False, 0, 0, 0.0, err)


class SimulatedJudge:
    """Dry-run judge. Knows the generator truth; errs at fixed rates."""

    simulated = True

    def __init__(self, truth: dict[int, str], sensitivity: float = 0.93, specificity: float = 0.88,
                 nd_rate: float = 0.04, seed: int = 11):
        self.truth, self.sens, self.spec, self.nd = truth, sensitivity, specificity, nd_rate
        self.rng = random.Random(seed)

    def __call__(self, note: str, pred: str, visit_id: int | None = None) -> Verdict:
        t = self.truth[visit_id]
        if self.rng.random() < self.nd:
            v = "not_determinable"
        elif pred == t:
            v = "correct" if self.rng.random() < self.sens else "incorrect"
        else:
            v = "incorrect" if self.rng.random() < self.spec else "correct"
        quote = note.split("\n")[-1][:80] if v != "not_determinable" else ""
        tok_in = (len(SYSTEM) + len(note)) // 4 + 20
        return Verdict(v, t if v == "incorrect" else (pred if v == "correct" else None), quote,
                       "simulated", True, tok_in, 60, 0.0)
