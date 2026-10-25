# Plan

Origin (Oct 2026): a request to evaluate BERT-family models from Hugging Face
for helping diagnose periodontal disease, alongside an OMOP tooth-level
modeling effort. Built in public on synthetic data until approved
for internal use; Databricks is the eventual home.

## Built (v0.1)

- [x] Model registry: 12 candidates from the evaluation sheet, roles, ladders (`models.yaml`)
- [x] OMOP 5.4 dental extension: `SITE`, `SITE_EVENT`, `perio_chart` view, `DENTAL_LOCAL` concepts
- [x] Perio chart → status rules (2017 AAP/EFP, severity axis), Python and R, parity-tested
- [x] Synthetic SOAP note renderer with shorthand, negation, and a no-leak mode
- [x] Stand-in population so everything runs without Java/Synthea
- [x] Patient-level split; shared scorer in Python and R with identical output
- [x] Rungs: rules, structured, TF-IDF (Python, run); HF fine-tune (Python, written);
      tidymodels baselines and `text` encoders (R, written)
- [x] Databricks Free Edition notebook (Python path + `ai_query` LLM rung)

## First result, and why it changes the next step

300 stand-in people, 754 notes, 154 test notes:

| rung | macro F1 | sensitivity | specificity |
|------|---------:|------------:|------------:|
| rules_baseline | 0.966 | 1.00 | 0.92 |
| structured_baseline | 0.918 | 0.99 | 1.00 |
| tfidf_logreg | 0.987 | 1.00 | 1.00 |

Python and R produce the same rules numbers to 1e-16.

**The synthetic notes are too easy.** The renderer writes the chart numbers
into the text almost verbatim, so a regex nearly matches the chart and there is
no headroom for a BERT model to show anything. Turning off the Assessment leak
barely moves it. Until the notes get harder, a 12-model comparison would only
be ranking noise.

## Next, in order

1. **Make the notes realistic enough to need a model.** In `notes.py`:
   - drop numbers in a share of notes and use descriptors instead
     ("generalized moderate horizontal bone loss", "localized 5-6 mm pockets
     posterior", "heavy BOP")
   - tooth-level findings from `SITE`/`SITE_EVENT` ("#3 #14 #19 PD 6mm MB/DL")
   - more shorthand, misspellings, copy-forward text from the previous visit
   - contradictions a clinician resolves (old Assessment line, new Objective)
   - success test: rules baseline drops well below TF-IDF, and TF-IDF below
     the chart-only structured baseline
2. **Have a dental clinician review 30 notes** for plausibility and fix the
   renderer from that. This is the only part that needs a dentist, and it is small.
3. **Write the Synthea perio module** (`synthea/modules/dental_periodontal_exam.json`)
   so charts progress across visits from age/smoking/diabetes instead of
   being drawn independently. Replaces `synthetic.py`.
4. **Run the classification ladder** on Free Edition: small models first
   (DistilBERT, BERT, SciBERT, BiomedBERT), then ModernBERT/BioClinical-ModernBERT
   if CPU time allows. Large models wait for paid compute.
5. **R side:** the R owner runs `install.R`, the ETL-Synthea
   load and the tidymodels baselines locally; fix what breaks.
6. **SapBERT** for concept mapping into `NOTE_NLP` / SNOMED; **GTE-ModernColBERT**
   for evidence retrieval. Separate tracks, separate metrics.
7. **Gate to internal use:** de-identification step and a clinician-labeled
   protocol replace `labels.py` as ground truth; move to the internal workspace.

## Open decisions

- R owner (README names them)
- Whether the first real task stays perio status or becomes something the data
  science side needs sooner
- Which LLM endpoint is the challenger once on a paid workspace
- A 13th candidate model was added after the sheet; name to be confirmed
