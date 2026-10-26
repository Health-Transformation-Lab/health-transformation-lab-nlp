# Feature Specification: De-identification methods compared on labeled fake PHI, with cost-effectiveness

**Feature Branch**: `007-deid-methods`

**Created**: 2026-10-25

**Status**: v1 implemented on synthetic data (local engines run; cloud engines wired and tested with fake clients, not run)

**Input**: "The de-identification logic looks weak. Implement alternative versions,
including Microsoft's de-identification and regex combined, and judge the cost-effectiveness
of these methods. Mark the records we know have PHI so we can test de-identification."

> Personal learning project; synthetic data; public sources only. Every name, date and number
> in the test set is invented. Nothing here describes any organization's de-identification setup.

## Context

The study's notes carry fake PHI the generator inserted, so every span is known. But the
built-in regex engine was tuned on the same note templates: it finds PHI because it knows
where the generator puts it. That proves the plumbing, not the method. A fair comparison
needs PHI in the shapes real notes have (names with no "Patient:" cue, relatives, ages over
89, emails, insurance IDs, odd date and phone formats) and dental text that looks like PHI
but isn't (Glickman and Miller classes, tooth numbers, CDT and ICD codes, probing readings
like 6-5-6). Over-redacting the dental terms damages the very text the classifiers read.

## User stories

### US1 - Labeled PHI challenge set (P1)
A seeded set of dental notes with every fake PHI span marked (start, end, type), in two
tiers: **easy** (header shapes the study notes use) and **hard** (prose shapes), plus
marked **dental decoys** that must survive.
- Categories follow HIPAA Safe Harbor's 18 identifiers and the 2014 i2b2/UTHealth
  de-identification annotation guidelines (patient, doctor, relative, age > 89, dates,
  phone, email, URL, SSN, medical record, health plan ID, street, city, ZIP, organization).
- Names come from a list the engines don't use (no dictionary can memorize the generator).
- **Given** a seed, **Then** the set is identical; every span's text equals the note slice.

### US2 - Engines (P1)
`regex` (existing), `regex_v2` (more shapes, relative/age cues, email, URL, SSN, plan IDs),
`presidio` (optional), `azure_deid` (Azure Health Data Services de-identification, TAG),
`azure_language` (Azure AI Language PII, healthcare domain), and **ensembles** (union of
engines, e.g. `azure_deid+regex_v2`). A **dental guard** drops spans that sit inside dental
terms. Cloud engines need endpoint and credential; parsing is tested with fake clients.

### US3 - Scores (P1)
Per engine and tier: entity recall (an entity counts as removed only if every character
is covered), character recall and precision, leaked identifiers per 1,000 notes, decoy damage
(share of dental decoys with any character redacted), recall by category.

### US4 - Cost-effectiveness (P1)
Cost per 1M notes = engine cost (local: measured throughput × node price; service: price per
MB or per 1,000-character record, minus a free allowance) + human review of notes the residual
scan flags. Frontier: dominated if another engine is cheaper and leaks no more; ICER =
extra USD per leaked identifier avoided. Python and R give the same frontier (parity test).
Prices default to placeholders marked ILLUSTRATIVE; list prices must be filled from the
vendor's pricing page.

## Out of scope
Running the cloud engines (needs an Azure resource; network blocked here). Real notes.
Re-identification risk (expert determination). Surrogate (fake-replacement) output.

## References
- HHS, Guidance regarding methods for de-identification of PHI (Safe Harbor, Expert Determination).
- Stubbs A, Uzuner Ö. Annotating longitudinal clinical narratives for de-identification: the 2014
  i2b2/UTHealth corpus. J Biomed Inform 2015;58(Suppl):S20–S29.
- Microsoft Learn, De-identification service in Azure Health Data Services (overview, pricing).
- Microsoft Learn, Azure AI Language: PII detection.
