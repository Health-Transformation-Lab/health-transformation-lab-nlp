# De-identification review protocol (spec 008)

> **Personal learning project.** Synthetic notes; every identifier is invented. See
> [DISCLAIMER](../DISCLAIMER.md). Set-up and scripts: [labelstudio/README.md](../labelstudio/README.md).

Two tasks, each in its own Label Studio project. Do them on your own; don't compare answers.

## Gold: mark every identifier in the original note

Highlight the **whole value and nothing else** ("Nakamura", not "Mrs Nakamura"; "3/4/2021", not
"on 3/4/2021"). Pick the category; the list follows the 2014 i2b2/UTHealth guidelines and HIPAA
Safe Harbor, the same as the test set ([deidentification.md](deidentification.md)).

| Category | Mark | Don't mark |
|---|---|---|
| PATIENT, RELATIVE | names, nicknames, initials of the patient or family | "Pt", "patient" |
| DOCTOR | clinicians' and staff names | "Dr" on its own, specialties |
| AGE | ages over 89 only | ages 89 and under |
| DATE | any date or part (day + month, month + year), DOB, DOS | years alone, "today", durations |
| PHONE, EMAIL, URL, SSN | the full value | |
| MEDICAL_RECORD, HEALTH_PLAN, ID_OTHER | record, member and other ID numbers | CDT (D4341) and ICD (K05.321) codes |
| STREET, CITY, ZIP | address parts smaller than a state | state names |
| ORGANIZATION | practice, clinic, employer names | product names (Arestin, Peridex) |

**Dental text is never PHI**: tooth numbers (#19), probing readings (6-5-6), Glickman and Miller
classes, instruments (Gracey 11/12), CDT and ICD codes, lab values.

**Pre-filled highlights** come from a de-identification engine, and some are wrong. Check every one:
fix the boundaries, change the category, delete false ones, add what it missed. `PHI_UNSPECIFIED`
means the engine couldn't tell what kind of identifier it is: always change it to a category.
Some notes have no pre-filled highlights on purpose. Annotate them the same way.

## QA: read de-identified notes

Tags like `[PATIENT]` or `[DATE]` mark what the engine removed. Read the rest.

1. **Does any identifier remain?** Highlight each one as `LEAK`, then answer yes. A partial leak
   counts ("[PATIENT]son" or a surviving surname). Pre-filled `LEAK` highlights come from an
   automatic scan: keep only real identifiers.
2. **Did redaction remove clinical meaning?** Yes if a tooth number, code, measurement or eponym
   was replaced by a tag.

## How it's scored
Gold: agreement between annotators, then a consensus each engine is scored against. QA: the share
of notes with a leak, with a 95% interval; on synthetic notes also how many real leaks reviewers
caught. Details: [labelstudio/README.md](../labelstudio/README.md).
