# What is a BERT model?

**In plain words:** BERT is a type of AI model that *reads* text. It does not write. It first
learns how English works by reading huge amounts of text, and then it is trained a little more
to do one specific job, such as "read this dental note and give the periodontal status".

## How it learns

1. **Pre-training (done once, by the model's authors).** The model reads billions of words
   (Wikipedia and books for the original BERT; PubMed papers or hospital notes for the medical
   versions). Words are hidden at random and the model has to guess them from the words around
   them, on both sides. "The patient has 6 mm [hidden] on #19" → "pockets". After enough of
   this, the model has learned what words mean in context.
2. **Fine-tuning (done here, on the reviewers' labels).** A small extra layer is added on top
   that picks one of our six labels (healthy, gingivitis, stage I–IV). The model is shown
   training notes with their correct labels and adjusts itself until its picks match. This takes
   minutes to hours, not the weeks pre-training takes.
3. **Prediction.** A new note goes in; one label and a confidence score for each label come out.

## Why "BERT"

Bidirectional Encoder Representations from Transformers ([Devlin et al., 2018](https://arxiv.org/abs/1810.04805)).

- **Bidirectional:** it looks at the words before *and* after each word at the same time. In
  "no bleeding on probing", "no" changes what "bleeding" means.
- **Encoder:** it turns text into numbers (one list of numbers per word, and one for the whole
  note) that a classifier can use. It does not generate text.
- **Transformer:** the neural network design ("attention") that lets every word look at every
  other word in the note.

## BERT vs an LLM like MedGemma

| | BERT-type encoder | LLM (MedGemma, GPT, Claude) |
|---|---|---|
| What it does | Reads; outputs a label or tags words | Reads and writes text |
| Size | 66M–400M numbers ("parameters") | 4B–27B+ |
| Hardware | Runs on a laptop CPU | Usually needs a GPU |
| Needs labeled training notes | Yes, a few hundred | No (prompt), or a few for examples |
| Explains its answer | No | Can write a reason (which can be wrong) |
| Same input, same output | Yes | Only with temperature 0 |

## The variants in this project

All 12 in [`models.yaml`](../models.yaml) are BERT or its descendants. They differ in three ways:

- **What they read first.** General text (BERT, DistilBERT, ModernBERT), science papers
  (SciBERT), biomedical papers (BiomedBERT, SapBERT) or clinical notes (BioClinical ModernBERT,
  Clinical-Longformer). A model that has seen clinical shorthand should need fewer labeled notes.
- **How much they read at once.** Original BERT stops at 512 word pieces (about 350 words); the
  rest of a long note is cut off. Longformer reads 4,096 and ModernBERT 8,192, enough for a whole
  visit note.
- **Size.** DistilBERT is a smaller, faster copy of BERT; "large" models are bigger and slower
  and sometimes more accurate.

SapBERT and GTE-ModernColBERT aren't classifiers: they match words to vocabulary concepts and find
similar passages ([rag_and_vocabulary.md](rag_and_vocabulary.md)).

## BERT for de-identification

The same design can label each word instead of the whole note ("token classification"): name,
date, phone, or not PHI. Two such models are scored in [deidentification.md](deidentification.md):
`hf_stanford` (a BERT trained on radiology reports and notes) and `hf_obi` (RoBERTa, a BERT
variant, trained on the i2b2 2014 notes). They tend to tag dental eponyms ("Glickman", "Miller")
as names, which is why the dental guard exists.

## Where it is in the code

- Classifier: [`rungs.py`](../python/health_transformation_lab_nlp/rungs.py) `HFEncoder` (fine-tune, predict);
  run with [`scripts/11_ai_predict.py`](../python/scripts/11_ai_predict.py).
- De-identification: [`deid.py`](../python/health_transformation_lab_nlp/deid.py) `detect_transformer`.
