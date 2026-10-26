"""A labeled fake-PHI challenge set for comparing de-identification methods (spec 007).

Every note is synthetic and every identifier is invented; each one is marked with its
character span and category, so recall and over-redaction are exact. Two tiers:

  easy  PHI in the header shapes the study notes use (Patient:, MRN:, DOB:, Dr.).
  hard  PHI in prose shapes real notes have: first name alone, lowercase names, relatives,
        Mrs without a period, ages over 89, odd date and phone formats, email, URL, SSN,
        health plan member IDs, street / city / ZIP, referral practices.

  unseen  shapes written AFTER regex_v2 and never used to tune it (a held-out test):
        ALL-CAPS and possessive names, names after "with" or "thanks", names that are
        words (Hope, Rose), O'/hyphenated names, nicknames in quotes, weekday dates,
        "the 14th", spaced phones, fax, apartment numbers, driver's licence, vehicle
        plate, device serial, IP address, social handle, employer.

All tiers also carry marked **dental decoys**: text that looks like PHI but isn't and must
survive (Glickman and Miller classes, Gracey 11/12, tooth numbers, CDT and ICD codes,
probing triplets such as 6-5-6, drug names, ages under 90). Over-redacting them damages
the text the classifiers read.

Categories follow HIPAA Safe Harbor's identifiers and the 2014 i2b2/UTHealth annotation
guidelines (Stubbs & Uzuner 2015). Ages of 89 and under, years alone and states are not PHI
under Safe Harbor, so they're decoys here, not PHI. Names come from lists the de-id engines
don't use, so no engine can pass by memorizing the generator. Emails and URLs use reserved
example domains; SSNs start with 9 (never issued).
"""

from __future__ import annotations

import datetime as dt
import random

CATEGORIES = ["PATIENT", "DOCTOR", "RELATIVE", "AGE", "DATE", "PHONE", "EMAIL", "URL", "SSN",
              "MEDICAL_RECORD", "HEALTH_PLAN", "STREET", "CITY", "ZIP", "ORGANIZATION", "ID_OTHER"]

CH_FIRST = ["Imani", "Bartholomew", "Svetlana", "Kwame", "Yusuf", "Ingrid", "Dmitri", "Lucia", "Tariq",
            "Beatriz", "Ngozi", "Hiroshi", "Esperanza", "Mateo", "Hope", "Faith", "Rhett", "Odalys"]
CH_LAST = ["Abernathy", "Kowalczyk", "Oyelaran", "Delacroix", "Featherstone", "Nakamura", "Villanueva",
           "Lindqvist", "Mbeki", "Castellano", "Whitaker", "Orozco", "Pemberton", "Achterberg"]
CH_CITIES = ["Northport", "Cottondale", "Brookwood", "Moundville", "Coker", "Duncanville"]
CH_STREETS = ["Juniper Way", "Riverbend Rd", "Magnolia Ct", "Old Greensboro Rd", "Willow Bend Dr"]
UNSEEN_FIRST = ["Rose", "Will", "Dawn", "Sunny", "Ezekiel", "Marisol", "Thaddeus", "Wren"]
UNSEEN_LAST = ["O'Shaughnessy", "Ruiz-Delgado", "McAllister", "Vandermeer", "Ng", "Abara"]
CH_ORGS = ["Oakhollow Periodontal Associates", "Riverbend Family Dental", "Northport Oral Surgery Center"]
RELATIVES = ["husband", "wife", "daughter", "son", "mother", "father", "sister", "caregiver"]
TEETH = [2, 3, 14, 15, 18, 19, 30, 31]


class _Note:
    def __init__(self):
        self.parts, self.phi, self.decoys, self.n = [], [], [], 0

    def t(self, s):
        self.parts.append(s)
        self.n += len(s)
        return self

    def _mark(self, lst, s, kind):
        lst.append({"start": self.n, "end": self.n + len(s), "text": s, "type": kind})
        return self.t(s)

    def p(self, s, kind):
        return self._mark(self.phi, s, kind)

    def d(self, s, kind):
        return self._mark(self.decoys, s, kind)

    def build(self, note_id, tier):
        return {"note_id": note_id, "tier": tier, "text": "".join(self.parts), "phi": self.phi, "decoys": self.decoys}


def _date(rng):
    return dt.date(2019, 1, 1) + dt.timedelta(days=rng.randint(0, 2000))


def _date_hard(rng):
    d = _date(rng)
    sfx = {1: "st", 2: "nd", 3: "rd"}.get(d.day if d.day < 20 else d.day % 10, "th")
    return rng.choice([f"{d:%B} {d.day}{sfx}, {d.year}", f"{d.day} {d:%b} {d.year}", f"{d:%d%b%Y}".upper(),
                       f"{d.month}/{d.day}/{d:%y}", f"{d:%b}. {d.day}"])


def _phone(rng):
    a, b, c = rng.randint(201, 989), rng.randint(200, 999), rng.randint(1000, 9999)
    return rng.choice([f"{a}.{b}.{c}", f"+1 {a} {b} {c}", f"{a}-{b}-{c}", f"({a}){b}-{c}"])


def _name(rng):
    return rng.choice(CH_FIRST), rng.choice(CH_LAST)


def _clinical(n: _Note, rng):
    """Dental findings with decoys; 3-4 sentences."""
    tooth = lambda: f"#{rng.choice(TEETH)}"
    sents = [
        lambda: n.t("Findings: ").d(f"Glickman class {rng.choice(['II', 'III'])}", "EPONYM").t(" furcation on ")
        .d(tooth(), "TOOTH").t(". "),
        lambda: n.d(f"Miller class {rng.choice(['I', 'II'])}", "EPONYM").t(" recession ").d(tooth(), "TOOTH").t(". "),
        lambda: n.t("PD ").d(f"{rng.randint(4, 7)}-{rng.randint(4, 7)}-{rng.randint(4, 7)}", "PROBING")
        .t(" mm MB-B-DB on ").d(tooth(), "TOOTH").t(". "),
        lambda: n.t("Tx plan: SRP UR/LR (").d("D4341", "CDT").t("), ").d("Arestin", "DRUG").t(" at ")
        .d(tooth(), "TOOTH").t(". "),
        lambda: n.t("Dx ").d(f"K05.3{rng.randint(1, 2)}{rng.randint(1, 3)}", "ICD").t("; ")
        .d(f"A1c {rng.randint(60, 89) / 10}%", "LAB").t(". "),
        lambda: n.d("Gracey 11/12", "INSTRUMENT").t(" used on ").d(tooth(), "TOOTH").t(". "),
        lambda: n.t("Rx ").d("Peridex", "DRUG").t(" 0.12% rinse BID. "),
        lambda: n.t("BOP 40%, generalized stage III grade B. "),
    ]
    for f in rng.sample(sents, rng.randint(3, 4)):
        f()


def _easy(rng, i):
    n = _Note()
    f, last = _name(rng)
    df, dl = _name(rng)
    n.t("Patient: ").p(f"{last}, {f}", "PATIENT").t(" (MRN: ").p(f"{rng.randint(10, 99)}{rng.randint(100000, 999999)}",
                                                           "MEDICAL_RECORD").t(")\n")
    n.t("DOB: ").p((dt.date(1935, 1, 1) + dt.timedelta(days=rng.randint(0, 25000))).strftime("%m/%d/%Y"), "DATE").t("  DOS: ").p(_date(rng).isoformat(), "DATE").t("\n")
    n.t("Provider: Dr. ").p(f"{df} {dl}", "DOCTOR").t("\n")
    _clinical(n, rng)
    n.t("Call ").p(f"({rng.randint(201, 989)}) {rng.randint(200, 999)}-{rng.randint(1000, 9999)}", "PHONE").t(" with questions.")
    return n.build(i, "easy")


def _hard(rng, i):
    n = _Note()
    f, last = _name(rng)
    rf, rl = _name(rng)
    df, dl = _name(rng)
    opts = [
        lambda: n.p(f, "PATIENT").t(" reports sensitivity on the lower left. "),
        lambda: n.t("pt ").p(f"{f.lower()} {last.lower()}", "PATIENT").t(" arrived 10 min late. "),
        lambda: n.t("Mrs ").p(last, "PATIENT").t(" declined SRP today; will reconsider. "),
        lambda: n.t("Spoke with her ").t(rng.choice(RELATIVES) + " ").p(f"{rf} {rl}", "RELATIVE").t(" about home care. "),
        lambda: n.p(str(rng.randint(90, 104)), "AGE").t(" yo presents for perio maintenance. "),
        lambda: n.t("Last cleaning ").p(_date_hard(rng), "DATE").t(". "),
        lambda: n.t("Call back at ").p(_phone(rng), "PHONE").t(". "),
        lambda: n.t("Pt emailed photos from ").p(f"{f.lower()}.{last.lower()}@example.org", "EMAIL").t(". "),
        lambda: n.t("Portal message: ").p(f"https://portal.example.org/msg/{rng.randint(10000, 99999)}", "URL").t(" "),
        lambda: n.t("SSN on file ").p(f"9{rng.randint(10, 99)}-{rng.randint(10, 99)}-{rng.randint(1000, 9999)}", "SSN").t(". "),
        lambda: n.t("Bluebird Dental Plan member ID ").p(f"W{rng.randint(100000000, 999999999)}", "HEALTH_PLAN").t(". "),
        lambda: n.t("MR# ").p(str(rng.randint(1000000, 9999999)), "MEDICAL_RECORD").t(". "),
        lambda: n.t("Lives at ").p(f"{rng.randint(10, 9999)} {rng.choice(CH_STREETS)}", "STREET").t(", ")
        .p(rng.choice(CH_CITIES), "CITY").t(", AL ").p(f"35{rng.randint(100, 999)}", "ZIP").t(". "),
        lambda: n.t("Referred to ").p(f"{df} {dl}", "DOCTOR").t(", DDS at ").p(rng.choice(CH_ORGS), "ORGANIZATION").t(". "),
        lambda: n.t("Per Dr ").p(dl, "DOCTOR").t(", recheck in 3 mo. "),
        lambda: n.d(str(rng.randint(40, 89)), "AGE_UNDER_90").t(" yo at first visit; history reviewed. "),
    ]
    picks = rng.sample(opts, rng.randint(5, 8))
    for k, fn in enumerate(picks):
        fn()
        if k == 1:
            _clinical(n, rng)
    return n.build(i, "hard")


def _unseen(rng, i):
    n = _Note()
    f, last = rng.choice(UNSEEN_FIRST), rng.choice(UNSEEN_LAST)
    rf, rl = rng.choice(UNSEEN_FIRST), rng.choice(UNSEEN_LAST)
    df, dl = rng.choice(UNSEEN_FIRST), rng.choice(UNSEEN_LAST)
    d = _date(rng)
    opts = [
        lambda: n.p(f"{f.upper()} {last.upper()}", "PATIENT").t(" - PERIO MAINT. "),
        lambda: n.p(f, "PATIENT").t("'s mom asked about the bleeding. "),
        lambda: n.t("Reviewed x-rays with ").p(f"{f} {last}", "PATIENT").t(" and discussed SRP. "),
        lambda: n.t("thanks, ").p(df, "DOCTOR").t(" - see note above. "),
        lambda: n.t("Goes by \"").p(rng.choice(["Kiki", "Bubba", "Tink", "Junior"]), "PATIENT").t("\". "),
        lambda: n.t("Brought by daughter ").p(rf, "RELATIVE").t(" ").p(rl, "RELATIVE").t(". "),
        lambda: n.t("Seen ").p(f"{d:%A} the {d.day}th", "DATE").t(". "),
        lambda: n.t("Ph ").p(f"{rng.randint(201, 989)} {rng.randint(200, 999)} {rng.randint(1000, 9999)}", "PHONE").t(". "),
        lambda: n.t("Fax records to ").p(f"{rng.randint(201, 989)}-{rng.randint(200, 999)}-{rng.randint(1000, 9999)}",
                                          "PHONE").t(" attn ").p(dl, "DOCTOR").t(". "),
        lambda: n.t("Address updated: ").p(f"Apt {rng.randint(1, 40)}{rng.choice('ABCD')}", "STREET").t(". "),
        lambda: n.t("DL ").p(f"{rng.randint(1000000, 9999999)}", "ID_OTHER").t(" checked at front desk. "),
        lambda: n.t("Plate ").p(f"{rng.randint(10, 99)}{rng.choice('ABCDEFGH')}{rng.randint(100, 999)}", "ID_OTHER")
        .t(" in handicap spot. "),
        lambda: n.t("Intraoral scanner SN ").p(f"IOS-{rng.randint(100000, 999999)}", "ID_OTHER").t(" logged. "),
        lambda: n.t("Telehealth from ").p(f"10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}", "URL").t(". "),
        lambda: n.t("Follows us on IG ").p(f"@{f.lower()}_{rng.randint(10, 99)}", "URL").t(". "),
        lambda: n.t("Works at ").p(f"{last} Lumber", "ORGANIZATION").t("; shifts limit appts. "),
        lambda: n.t("Referred by ").p(f"Dr. {df} {dl}", "DOCTOR").t(". "),
    ]
    for k, fn in enumerate(rng.sample(opts, rng.randint(5, 8))):
        fn()
        if k == 1:
            _clinical(n, rng)
    return n.build(i, "unseen")


def build_challenge(n_notes: int = 400, seed: int = 7, hard_share: float = 0.35,
                    unseen_share: float = 0.3) -> list[dict]:
    """n_notes labeled notes in three tiers (the rest easy), in seeded random order."""
    rng = random.Random(seed)
    n_hard, n_unseen = round(n_notes * hard_share), round(n_notes * unseen_share)
    tiers = ["hard"] * n_hard + ["unseen"] * n_unseen + ["easy"] * (n_notes - n_hard - n_unseen)
    rng.shuffle(tiers)
    make = {"easy": _easy, "hard": _hard, "unseen": _unseen}
    return [make[t](rng, i) for i, t in enumerate(tiers)]


def load_external(path, text_keys=("text", "query", "note"), tier: str = "external") -> list[dict]:
    """Load another labeled PHI set (e.g. ASQ-PHI, MIT) into the challenge format.

    JSONL or JSON list. Each record has its text under one of text_keys and a list of PHI under
    "phi" (or "entities" / "labels"), each either {start, end, type} or {value | text, type}; a
    value without offsets is located in the text (every occurrence). Records with no PHI are kept:
    they're hard negatives, and anything an engine removes from them is over-redaction.
    ASQ-PHI's own release (synthetic_clinical_queries.txt: "===QUERY===" then "===PHI_TAGS===" with
    one {"identifier_type", "value"} JSON per line) is read as is."""
    import json
    from pathlib import Path
    if str(path).endswith(".csv"):
        return _load_jsl_csv(path, tier)
    raw = Path(path).read_text()
    if raw.lstrip().startswith("===QUERY==="):
        data = _parse_asq_phi(raw)
    else:
        data = json.loads(raw) if raw.lstrip().startswith("[") else [json.loads(x) for x in raw.splitlines() if x.strip()]
    out = []
    for i, r in enumerate(data):
        text = next((r[k] for k in text_keys if k in r), None)
        if text is None:
            raise KeyError(f"record {i}: no text field among {text_keys}")
        ents = r.get("phi", r.get("entities", r.get("labels", []))) or []
        spans = []
        for e in ents:
            kind = str(e.get("type", e.get("label", "PHI")))
            if "start" in e and "end" in e:
                spans.append({"start": int(e["start"]), "end": int(e["end"]),
                              "text": text[int(e["start"]):int(e["end"])], "type": kind})
                continue
            val = str(e.get("value", e.get("text", "")))
            j = text.find(val) if val else -1
            while j >= 0:
                spans.append({"start": j, "end": j + len(val), "text": val, "type": kind})
                j = text.find(val, j + len(val))
        out.append({"note_id": r.get("id", i), "tier": tier, "text": text,
                    "phi": sorted(spans, key=lambda s: s["start"]), "decoys": []})
    return out


def _load_jsl_csv(path, tier: str) -> list[dict]:
    """John Snow Labs' de-identification benchmark CSV (doc_id, text, begin, end, chunk, chunk_label;
    one row per labeled chunk, end exclusive). Its notes look like i2b2 discharge summaries: keep the
    file outside the repo (data/raw/)."""
    import pandas as pd
    df = pd.read_csv(path)
    out = []
    for doc_id, g in df.groupby("doc_id", sort=True):
        text = g.text.iloc[0]
        g = g.dropna(subset=["begin", "end"])
        phi = [{"start": int(b), "end": int(e), "text": text[int(b):int(e)], "type": str(lab)}
               for b, e, lab in zip(g.begin, g.end, g.chunk_label)]
        out.append({"note_id": f"jsl-{doc_id}", "tier": tier, "text": text,
                    "phi": sorted(phi, key=lambda x: x["start"]), "decoys": []})
    return out


def _parse_asq_phi(raw: str) -> list[dict]:
    import json
    out = []
    for block in raw.split("===QUERY===")[1:]:
        query, _, tags = block.partition("===PHI_TAGS===")
        phi = [json.loads(x) for x in tags.splitlines() if x.strip()]
        out.append({"query": query.strip(),
                    "phi": [{"value": t["value"], "type": t["identifier_type"]} for t in phi]})
    return out


def load_i2b2_2014(folder, tier: str = "i2b2_2014") -> list[dict]:
    """The 2014 i2b2/UTHealth (n2c2) de-identification corpus: one XML per note, text in <TEXT>,
    PHI as <TAGS> children with start, end, text and TYPE. Needs the n2c2 data use agreement;
    keep it outside the repo (never commit it)."""
    import xml.etree.ElementTree as ET
    from pathlib import Path
    out = []
    for f in sorted(Path(folder).glob("*.xml")):
        root = ET.parse(f).getroot()
        text = root.findtext("TEXT") or ""
        phi = [{"start": int(e.get("start")), "end": int(e.get("end")), "text": e.get("text", ""),
                "type": e.get("TYPE", e.tag)} for e in (root.find("TAGS") or [])]
        out.append({"note_id": f.stem, "tier": tier, "text": text, "phi": sorted(phi, key=lambda s: s["start"]),
                    "decoys": []})
    return out
