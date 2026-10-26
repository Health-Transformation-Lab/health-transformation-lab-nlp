# Label Studio setup

**Rule: only de-identified text goes into Label Studio.** The tasks file
`data/datasets/review_tasks.json` is built only from notes that passed the
final de-identification check (the "leak gate" in `study.py`: any note where a known identifier
survived is held back). With real data, Label Studio runs inside the approved
secure environment and still receives only de-identified notes.

## 1. Run Label Studio locally (synthetic data)

```bash
pip install label-studio            # or: docker run -it -p 8080:8080 -v $(pwd)/ls-data:/label-studio/data heartexlabs/label-studio:latest
label-studio start                  # opens http://localhost:8080
```

## 2. One project per reviewer

Independent staging is the point of the reliability study, so each reviewer
gets their own project and can't see anyone else's answers:

1. *Create Project* → name it `perio-review-<reviewer>`.
2. *Labeling Setup* → *Custom template* → paste `chart_review.xml`.
3. *Import* → `data/datasets/review_tasks.json` (240 charts).
4. Share the project with that reviewer only.
5. Give every reviewer `docs/labeling_protocol.md` before they start.

(One shared project with several annotators per task also works if your
Label Studio edition supports task overlap settings. Separate projects work on
every edition.)

## 3. Export and import

When a reviewer finishes: *Export* → *JSON*. Then:

```bash
cd python
python scripts/12_import_review.py reviewer1.json reviewer2.json reviewer3.json reviewer4.json
python scripts/13_reliability.py            # or, in R: Rscript r/R/04_reliability.R
```

## 4. Dry run without reviewers

```bash
python scripts/12_import_review.py --simulate 4
python scripts/13_reliability.py --simulated
```

Simulated files are named `simulated_*`, and the output says so. They test the
plumbing. They are not results.

## What the config captures

| Field | Type | Used for |
|-------|------|----------|
| `status` | single choice (6 + cannot_determine) | reliability, consensus gold |
| `grade`, `extent` | single choice | secondary outcomes |
| `decided_by` | multi choice of the evidence types (note, exam form, procedure codes and diagnoses completed/planned, probing chart, radiograph) | which evidence types reviewers trust → the rule-based algorithm |
| `conflict` | yes/no | how often evidence types disagree, per reviewer |
| `confidence` | 1–5 rating | stratify agreement by confidence |
| `evidence` | span labels on the note | training and scoring entity extraction |
| `comment` | free text | qualitative review |
