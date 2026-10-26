"""De-identification: find PHI spans in a note and replace them with tags.

Nothing reaches Label Studio (or any model) until it has passed through here
AND the leak gate. Two engines:

  regex     built in. Context patterns (Patient:, Pt, Dr., MRN, DOS ...),
            date / phone / ID / street-address shapes, and a capitalised
            name-pair heuristic, with an allowlist of dental terms so
            abbreviations like BOP, SRP, MB, DL, FMX are never redacted (the
            earlier de-id failed exactly there). Baseline; tuned on the
            synthetic note formats, so it will under-perform on real notes.
  regex_v2  regex plus the shapes real notes have (spec 007): names after
            relatives, Mrs/Mr/Dr without a period, "Name, DDS", lowercase "pt name
            name"; ages over 89; email, URL, SSN, health plan member IDs, MR#;
            dotted / +1 / spaced phones; written-out dates; street, city, ZIP.
  presidio  Microsoft Presidio (spaCy NER + recognisers) with the same dental
            allowlist. pip install presidio-analyzer and a spaCy model.
  azure_deid      Azure Health Data Services de-identification service (TAG):
                  ML models for 27 PHI categories. pip install
                  azure-health-deidentification azure-identity; AZURE_DEID_ENDPOINT.
  azure_language  Azure AI Language PII detection, healthcare (PHI) domain.
                  pip install azure-ai-textanalytics; AZURE_LANGUAGE_ENDPOINT, _KEY.
  hf_stanford     transformer NER trained for clinical de-identification:
                  StanfordAIMI/stanford-deidentifier-base (Chambon et al., JAMIA 2023; MIT).
  hf_obi          obi/deid_roberta_i2b2 (RoBERTa on i2b2 2014; MIT). Both need the
                  Hugging Face download (pip install -e ".[models]").
  llm             an LLM asked to list every identifier verbatim (any OpenAI-compatible
                  endpoint, e.g. a Databricks serving endpoint): DEID_LLM_BASE_URL,
                  DEID_LLM_MODEL, DEID_LLM_API_KEY. Values it lists that aren't in the
                  note are dropped (no invented identifiers).

Engines combine with "+": "azure_deid+regex_v2+guard" is the union of both
engines' spans, then the **dental guard**, which drops any span lying inside a
dental term (Glickman class II, Gracey 11/12, #19, D4341, K05.321, 6-5-6 ...):
general-purpose PHI models tag eponyms as names and probing readings as dates.

On synthetic notes every PHI span is known (phi.py), so `score_deid` measures
recall and over-redaction exactly and `leak_check` fails hard if any injected
value survives. On real notes the gate is `residual_scan` (re-run detectors on
the output) plus a human review sample, because nothing is known in advance.
"""

from __future__ import annotations

import re

DENTAL_ALLOWLIST = {
    "BOP", "CAL", "RBL", "PD", "SRP", "FMX", "BWX", "PAN", "PSR", "WNL", "MB", "DB", "ML", "DL", "B", "L",
    "M", "D", "OHI", "RTC", "FM", "UR", "LR", "UL", "LL", "HTN", "NKDA", "T2DM", "A1c", "AAP", "EFP",
    "Dx", "Tx", "Pt", "Hx", "Med", "Exam", "Impression", "Patient", "Provider", "DOS", "MRN", "DOB",
    "Stage", "Grade", "Generalized", "Localized", "Gen", "Loc", "Perio", "Periodontitis", "Gingivitis",
    "Plaque", "Dental", "Clinical", "Case", "Type", "Prophy", "Recall", "Referred", "Referral", "Next",
    "PERIODONTAL", "CHARTING", "COMPLETED", "Findings", "See", "Adult", "Pt's", "Dr", "Mr", "Mrs", "Ms", "I", "II", "III", "IV", "A", "C", "Gr", "St",
    # title-case diagnosis wording seen in real notes (spec 001)
    "Diagnosis", "Gingival", "Inflammation", "Recession", "Health", "Intact", "Periodontium",
    "Biofilm", "Calculus", "Bone", "Loss", "Chronic", "Severe", "Moderate", "Slight", "Mild",
    "CC", "MHx", "NV", "BP", "BWX", "PA", "Rx",
}

_NAME_WORD = r"[A-Z][a-z]+(?:-[A-Z][a-z]+)?"
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("NAME", re.compile(rf"(?<=Patient: )({_NAME_WORD}, {_NAME_WORD})")),
    ("NAME", re.compile(rf"(?<=\bPt )({_NAME_WORD} {_NAME_WORD})(?= \()")),
    ("NAME", re.compile(rf"(?<=\bDr\. )({_NAME_WORD}(?: {_NAME_WORD})?)")),
    ("ID", re.compile(r"(?<=MRN: )(\d{6,10})")),
    ("ID", re.compile(r"(?<=\()(\d{7,10})(?=\))")),
    ("ID", re.compile(r"\b(\d{8,10})\b")),
    ("DATE", re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}|"
                        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, \d{4})\b")),
    ("PHONE", re.compile(r"(\(\d{3}\) ?\d{3}-\d{4}|\b\d{3}-\d{3}-\d{4}\b)")),
    ("LOCATION", re.compile(r"(\d{1,5} (?:[A-Z0-9][a-z0-9]* )+(?:St|Ave|Street|Dr|Rd|Ln|Blvd|Ct)\b(?:, [A-Z][a-z]+)?)")),
    ("LOCATION", re.compile(rf"({_NAME_WORD} (?:Periodontics|Dental Group|Family Dentistry|Dental|Clinic))")),
]
_CAP_PAIR = re.compile(rf"\b({_NAME_WORD}) ({_NAME_WORD})\b")


def _merge(spans: list[dict]) -> list[dict]:
    spans = sorted(spans, key=lambda s: (s["start"], -s["end"]))
    out: list[dict] = []
    for s in spans:
        if out and s["start"] < out[-1]["end"]:
            out[-1]["end"] = max(out[-1]["end"], s["end"])
        else:
            out.append(dict(s))
    return out


def detect_regex(text: str) -> list[dict]:
    spans = []
    for kind, pat in _PATTERNS:
        for m in pat.finditer(text):
            spans.append({"start": m.start(1), "end": m.end(1), "type": kind})
    for m in _CAP_PAIR.finditer(text):
        if m.group(1) not in DENTAL_ALLOWLIST and m.group(2) not in DENTAL_ALLOWLIST:
            spans.append({"start": m.start(), "end": m.end(), "type": "NAME"})
    return _merge(spans)


def detect_presidio(text: str) -> list[dict]:  # pragma: no cover - optional dependency
    from presidio_analyzer import AnalyzerEngine
    global _PRESIDIO
    try:
        engine = _PRESIDIO
    except NameError:
        engine = _PRESIDIO = AnalyzerEngine()
    res = engine.analyze(text=text, language="en", allow_list=sorted(DENTAL_ALLOWLIST),
                         entities=["PERSON", "DATE_TIME", "PHONE_NUMBER", "LOCATION", "US_SSN",
                                   "EMAIL_ADDRESS", "MEDICAL_LICENSE", "US_DRIVER_LICENSE"])
    kind = {"PERSON": "NAME", "DATE_TIME": "DATE", "PHONE_NUMBER": "PHONE", "LOCATION": "LOCATION"}
    spans = [{"start": r.start, "end": r.end, "type": kind.get(r.entity_type, "ID")} for r in res]
    return _merge(spans + [s for s in detect_regex(text) if s["type"] == "ID"])


_NAME_ANY = rf"{_NAME_WORD}(?: {_NAME_WORD})?"
_MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
_PATTERNS_V2: list[tuple[str, re.Pattern]] = [
    ("NAME", re.compile(rf"\b(?:husband|wife|daughter|son|mother|father|sister|brother|spouse|partner|caregiver) "
                        rf"({_NAME_ANY})")),
    ("NAME", re.compile(rf"\b(?:Mrs|Mr|Ms|Dr|Miss)\.? ({_NAME_WORD}(?: {_NAME_WORD})?)")),
    ("NAME", re.compile(rf"({_NAME_ANY})(?=, (?:DDS|DMD|RDH|MD|DO|NP|PA)\b)")),
    ("NAME", re.compile(r"(?<=\bpt )([a-z]{3,} [a-z]{3,})(?= (?:arrived|seen|presents|reports|called|states))")),
    ("NAME", re.compile(rf"(?:^|(?<=\. ))({_NAME_WORD})(?= (?:reports|states|presents|called|declined|arrived))")),
    ("AGE", re.compile(r"\b(9\d|1[01]\d)(?=[ -]?(?:yo\b|y/o|y\.o\.|year-old|years? old))")),
    ("EMAIL", re.compile(r"([\w.+-]+@[\w-]+(?:\.[\w-]+)+)")),
    ("URL", re.compile(r"(https?://\S+|www\.\S+)")),
    ("ID", re.compile(r"\b(\d{3}-\d{2}-\d{4})\b")),
    ("ID", re.compile(r"(?i:member id|member #|subscriber id|policy #?|MR#|MRN#?|record #)\s*:?\s*([A-Z]{0,3}\d{5,12})")),
    ("PHONE", re.compile(r"((?:\+1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]\d{4})\b")),
    ("DATE", re.compile(rf"\b({_MONTHS} \d{{1,2}}(?:st|nd|rd|th)?(?:, \d{{4}})?|\d{{1,2}} {_MONTHS} \d{{4}}|"
                        r"\d{2}(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\d{4})\b")),
    ("LOCATION", re.compile(r"(\d{1,5} (?:[A-Z][a-z]+ ){1,3}(?:St|Ave|Street|Dr|Rd|Ln|Blvd|Ct|Way|Pl|Pkwy)\b)")),
    ("LOCATION", re.compile(rf"({_NAME_WORD})(?=, [A-Z]{{2}} \d{{5}})")),
    ("LOCATION", re.compile(r"(?<=\b[A-Z]{2} )(\d{5}(?:-\d{4})?)\b")),
    ("LOCATION", re.compile(rf"((?:{_NAME_WORD} ){{1,3}}(?:Periodontal Associates|Periodontics|Dental Group|"
                            r"Family Dental|Family Dentistry|Oral Surgery Center|Dental|Clinic|Hospital|Medical Center))")),
]


_PT_NAME = re.compile(rf"\b(?:Pt|Patient|pt)\.?:? ({_NAME_WORD}(?: {_NAME_WORD})?)")
# v1's capitalised-pair scan is non-overlapping, so "Pt Imani Featherstone" is read as the
# rejected pair (Pt, Imani) and then "Featherstone" alone. v2 scans every pair (lookahead).
_CAP_PAIR_OVERLAP = re.compile(rf"(?=\b({_NAME_WORD}) ({_NAME_WORD})\b)")


def detect_regex_v2(text: str) -> list[dict]:
    spans = detect_regex(text)
    for kind, pat in [*_PATTERNS_V2, ("NAME", _PT_NAME)]:
        for m in pat.finditer(text):
            spans.append({"start": m.start(1), "end": m.end(1), "type": kind})
    for m in _CAP_PAIR_OVERLAP.finditer(text):
        a, b = m.group(1), m.group(2)
        if a not in DENTAL_ALLOWLIST and b not in DENTAL_ALLOWLIST:
            spans.append({"start": m.start(1), "end": m.end(2), "type": "NAME"})
    return _merge(spans)


# Dental text that PHI detectors mistake for names, dates, IDs or phone numbers.
_DENTAL_PROTECT = re.compile(
    r"\b(?:Glickman|Miller|Hamp|Nabers|Gracey|Columbia|Langer|Lindhe)\b(?: (?:class|degree|grade|curette|probe))?"
    r"(?: [IV]+\b| \d+(?:/\d+)?)?"
    r"|#\d{1,2}\b|\b(?:teeth|tooth) \d{1,2}(?:-\d{1,2})?\b"
    r"|\bD\d{4}\b|\bK0\d\.\d{1,3}\b"
    r"|\b\d{1,2}-\d{1,2}-\d{1,2}\b(?! ?\d)|\b\d{1,2}/\d{1,2}(?: ?mm)\b"
    r"|\b(?:Peridex|Arestin|Atridox|PerioChip|chlorhexidine|doxycycline)\b"
    r"|\bA1c \d+(?:\.\d)?%?|\b(?:[1-8]\d|[1-9]) ?(?:yo|y/o)\b"
)


def dental_guard(text: str, spans: list[dict]) -> list[dict]:
    """Drop spans that lie entirely inside a dental term."""
    protected = [(m.start(), m.end()) for m in _DENTAL_PROTECT.finditer(text)]
    return [s for s in spans if not any(a <= s["start"] and s["end"] <= b for a, b in protected)]


# --------------------------------------------------------------- Microsoft services
_AZURE_DEID_TYPES = {"Patient": "PATIENT", "Doctor": "DOCTOR", "Age": "AGE", "Date": "DATE", "Phone": "PHONE",
                     "Fax": "PHONE", "Email": "EMAIL", "Url": "URL", "SocialSecurity": "ID", "MedicalRecord": "ID",
                     "HealthPlan": "ID", "IDNum": "ID", "Account": "ID", "License": "ID", "Street": "LOCATION",
                     "City": "LOCATION", "Zip": "LOCATION", "State": "LOCATION", "CountryOrRegion": "LOCATION",
                     "LocationOther": "LOCATION", "Hospital": "LOCATION", "Organization": "LOCATION"}
_AZURE_LANG_TYPES = {"Person": "NAME", "PhoneNumber": "PHONE", "Email": "EMAIL", "URL": "URL", "DateTime": "DATE",
                     "Date": "DATE", "Age": "AGE", "Address": "LOCATION", "Organization": "LOCATION",
                     "USSocialSecurityNumber": "ID", "IPAddress": "ID"}
_CLIENTS: dict = {}


def _need(var: str) -> str:
    import os
    v = os.environ.get(var)
    if not v:
        raise RuntimeError(f"{var} is not set: this engine calls an external service (synthetic or de-identified data only)")
    return v


def _azure_deid_client():  # pragma: no cover - needs an Azure resource
    if "deid" not in _CLIENTS:
        endpoint = _need("AZURE_DEID_ENDPOINT")
        from azure.health.deidentification import DeidentificationClient
        from azure.identity import DefaultAzureCredential
        _CLIENTS["deid"] = DeidentificationClient(endpoint, DefaultAzureCredential())
    return _CLIENTS["deid"]


def detect_azure_deid(text: str, client=None) -> list[dict]:
    """Azure Health Data Services de-identification, TAG operation (spans only, nothing replaced)."""
    client = client or _azure_deid_client()
    res = client.deidentify_text({"inputText": text, "operation": "Tag"})
    ents = res.tagger_result.entities if res.tagger_result else []
    return _merge([{"start": e.offset.code_point, "end": e.offset.code_point + e.length.code_point,
                    "type": _AZURE_DEID_TYPES.get(str(e.category), "ID")} for e in ents])


def _azure_language_client():  # pragma: no cover - needs an Azure resource
    if "lang" not in _CLIENTS:
        endpoint, key = _need("AZURE_LANGUAGE_ENDPOINT"), _need("AZURE_LANGUAGE_KEY")
        from azure.ai.textanalytics import TextAnalyticsClient
        from azure.core.credentials import AzureKeyCredential
        _CLIENTS["lang"] = TextAnalyticsClient(endpoint, AzureKeyCredential(key))
    return _CLIENTS["lang"]


def detect_azure_language(text: str, client=None) -> list[dict]:
    """Azure AI Language PII detection with the healthcare (PHI) domain filter."""
    client = client or _azure_language_client()
    doc = client.recognize_pii_entities([text], domain_filter="phi", language="en")[0]
    if getattr(doc, "is_error", False):
        raise RuntimeError(f"Azure AI Language error: {doc.error}")
    return _merge([{"start": e.offset, "end": e.offset + e.length,
                    "type": _AZURE_LANG_TYPES.get(str(e.category), "ID")} for e in doc.entities])


# --------------------------------------------------------------- AI: transformer NER, LLM
_HF_TYPES = {"PATIENT": "NAME", "STAFF": "NAME", "DOCTOR": "NAME", "PERSON": "NAME", "NAME": "NAME",
             "DATE": "DATE", "AGE": "AGE", "PHONE": "PHONE", "FAX": "PHONE", "EMAIL": "EMAIL", "URL": "URL",
             "WEB": "URL", "LOC": "LOCATION", "LOCATION": "LOCATION", "HOSP": "LOCATION", "HOSPITAL": "LOCATION",
             "PATORG": "LOCATION", "VENDOR": "LOCATION", "ID": "ID", "OTHERPHI": "ID"}
_HF_MODELS = {"hf_stanford": "StanfordAIMI/stanford-deidentifier-base", "hf_obi": "obi/deid_roberta_i2b2"}
_PIPES: dict = {}


def _join_adjacent(text: str, spans: list[dict], max_gap: int = 1) -> list[dict]:
    """Word pieces of one entity ('Kwame' + 'Oyelaran') come back as separate spans; join them."""
    out: list[dict] = []
    for s in sorted(spans, key=lambda s: s["start"]):
        if out and s["type"] == out[-1]["type"] and 0 <= s["start"] - out[-1]["end"] <= max_gap \
                and not text[out[-1]["end"]:s["start"]].strip():
            out[-1]["end"] = max(out[-1]["end"], s["end"])
        else:
            out.append(dict(s))
    return out


def _hf_pipe(model: str):  # pragma: no cover - needs the Hugging Face download
    if model not in _PIPES:
        from transformers import pipeline
        _PIPES[model] = pipeline("token-classification", model=model, aggregation_strategy="simple")
    return _PIPES[model]


def detect_transformer(text: str, model: str = _HF_MODELS["hf_stanford"], pipe=None, min_score: float = 0.5) -> list[dict]:
    """Clinical de-identification transformer (token classification). Labels may carry BIO/BILOU prefixes."""
    pipe = pipe or _hf_pipe(model)
    spans = []
    for e in pipe(text):
        label = re.sub(r"^[BILUES]-", "", str(e.get("entity_group", e.get("entity", ""))))
        if label in ("O", "") or float(e.get("score", 1.0)) < min_score:
            continue
        spans.append({"start": int(e["start"]), "end": int(e["end"]), "type": _HF_TYPES.get(label.upper(), "ID")})
    return _merge(_join_adjacent(text, spans))


LLM_DEID_SYSTEM = """You de-identify dental chart notes. List every piece of protected health information
(HIPAA Safe Harbor identifiers): names of patients, relatives, clinicians and staff; dates (except the year
alone); ages over 89; phone and fax numbers; emails; URLs; IP addresses; social security, record, health
plan, account, licence, vehicle and device numbers; street addresses, cities and ZIP codes; employers and
practice names. Copy each one verbatim, exactly as it appears in the note.
Do NOT list clinical text: tooth numbers (#19), probing readings (6-5-6), CDT and ICD codes (D4341,
K05.321), eponymous classifications and instruments (Glickman class II, Miller class I, Gracey 11/12),
drug names, lab values, or ages under 90.
Answer with JSON only: [{"text": "...", "type": "NAME|DATE|AGE|PHONE|EMAIL|URL|ID|LOCATION"}]"""
LLM_DEID_PROMPT_VERSION = "llm-deid-v1"


def _llm_complete(system: str, user: str) -> str:  # pragma: no cover - needs an endpoint
    import json
    import urllib.request
    base, model, key = _need("DEID_LLM_BASE_URL").rstrip("/"), _need("DEID_LLM_MODEL"), _need("DEID_LLM_API_KEY")
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 800,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(f"{base}/chat/completions", data=body, method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def detect_llm(text: str, complete=None) -> list[dict]:
    """LLM lists identifiers verbatim; each is located in the note (every occurrence). Values not
    found in the note are dropped, so the model can't add identifiers that aren't there."""
    import json
    if complete is None:
        _need("DEID_LLM_BASE_URL")
        complete = _llm_complete
    raw = complete(LLM_DEID_SYSTEM, f"Note:\n<<<\n{text}\n>>>")
    s = raw.strip()
    items = json.loads(s[s.find("["):s.rfind("]") + 1]) if "[" in s else []
    spans = []
    for it in items:
        val = str(it.get("text", "")).strip()
        j = text.find(val) if val else -1
        while j >= 0:
            spans.append({"start": j, "end": j + len(val), "type": str(it.get("type", "ID")).upper()})
            j = text.find(val, j + len(val))
    return _merge(spans)


ENGINES = {"regex": detect_regex, "regex_v2": detect_regex_v2, "presidio": detect_presidio,
           "azure_deid": detect_azure_deid, "azure_language": detect_azure_language,
           "hf_stanford": lambda text: detect_transformer(text, _HF_MODELS["hf_stanford"]),
           "hf_obi": lambda text: detect_transformer(text, _HF_MODELS["hf_obi"]),
           "llm": detect_llm}
CLOUD_ENGINES = {"azure_deid", "azure_language", "llm"}


def get_engine(spec: str):
    """'regex', 'regex_v2+guard', 'azure_deid+regex_v2+guard': union of engines, then optional dental guard."""
    parts = spec.split("+")
    guard = "guard" in parts
    names = [p for p in parts if p != "guard"]
    unknown = [p for p in names if p not in ENGINES]
    if unknown or not names:
        raise KeyError(f"unknown engine(s) {unknown or spec}; known: {sorted(ENGINES)} (+guard)")
    fns = [ENGINES[n] for n in names]

    def detect(text: str) -> list[dict]:
        spans = _merge([s for f in fns for s in f(text)])
        return dental_guard(text, spans) if guard else spans
    detect.__name__ = spec
    return detect


def redact(text: str, spans: list[dict]) -> str:
    out, last = [], 0
    for s in sorted(spans, key=lambda s: s["start"]):
        out.append(text[last:s["start"]])
        out.append(f"[{s['type']}]")
        last = s["end"]
    out.append(text[last:])
    return "".join(out)


def deidentify(text: str, engine: str = "regex") -> tuple[str, list[dict]]:
    spans = get_engine(engine)(text)
    return redact(text, spans), spans


# ------------------------------------------------------------ gates & scoring
def leak_check(deid_text: str, known_phi: list[dict]) -> list[str]:
    """Synthetic data only: every injected PHI value that survived (should be [])."""
    return [p["text"] for p in known_phi if p["text"] in deid_text]


def residual_scan(deid_text: str) -> list[dict]:
    """Real data: detectors re-run on the output. Non-empty = hold for human review."""
    return detect_regex(deid_text)


def score_deid(text: str, known_phi: list[dict], found: list[dict]) -> dict:
    """Character-level recall (PHI removed) and over-redaction (non-PHI removed)."""
    phi = set()
    for p in known_phi:
        phi.update(range(p["start"], p["end"]))
    red = set()
    for s in found:
        red.update(range(s["start"], s["end"]))
    return {"phi_chars": len(phi), "phi_chars_removed": len(phi & red),
            "non_phi_chars_removed": len(red - phi)}
