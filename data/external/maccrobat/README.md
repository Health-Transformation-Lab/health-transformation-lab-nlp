# MACCROBAT (public data)

**Not synthetic.** 200 clinical case reports from PubMed Central, already published and
de-identified, edited by the dataset's author to the case details and annotated by hand. Kept here
as external evaluation and training data under the public-dataset exception (constitution v1.2.0);
never mixed into this project's synthetic data and never presented as its patient records.

| | |
|---|---|
| Source | Caufield, J. Harry (2019). *MACCROBAT*. figshare. Dataset. https://doi.org/10.6084/m9.figshare.9764942.v2 |
| File | `MACCROBAT2020.zip`, the 2020 release (figshare file 21489405), unchanged. MD5 `9d090f3e0719e77e7a33c38750548bb8` (figshare's published checksum) |
| Licence | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution as above; changes listed below |
| Format | 200 pairs of `NNN.txt` (text, one sentence per line) and `NNN.ann` (brat standoff: entity type, character offsets, text; events and relations), named by PubMed ID |

## Files derived here (changes made)

| Path | What | Made by |
|---|---|---|
| `bio/train.txt`, `bio/val.txt`, `bio/test.txt` | The annotations filtered to `Age`, `Sex` and `Date` (all other types become `O`), split by document (seed 42; `phi_tagger.three_way_split`): 40 test notes, then 20 of the remaining 160 held out for validation, 140 train. Where two of these labels overlap, the first in the `.ann` file wins (3 of 1,133 entities lost, e.g. a phrase labelled both Age and Date). One `word tag` per line, blank line between sentences, `-DOCSTART- O` before each note. Words are `\w+` runs or single punctuation marks | `python/scripts/33_maccrobat_phi_tagger.py` (`phi_tagger.bio_docs`, `split_docs`, `write_conll`) |
| `course/train.txt`, `course/test.txt`, `course/labels.txt` | BIO files distributed with a course assignment on this dataset (de-identification as sequence classification), committed unchanged as received: 160 / 40 notes, `word POS tag` per line, 6 labels (no `I-Sex`). Made by the course's own preprocessing, not this repo's. Known defect: a word that ends a sentence keeps its period ("2005."), and such a word inside an entity is tagged `O`, cutting 88 training and 16 test dates short | course preprocessing; read by `phi_tagger.read_conll`, used by `33_maccrobat_phi_tagger.py --conll-dir` |
| `errors/<run>_val.txt`, `errors/<run>_test.txt` | Every entity the model alone (no post-processing) got wrong, gold or predicted, with type, words and context. Error analysis reads `_val`; `_test` is for the final report | `python/scripts/34_phi_tagger_regex.py` |

Used by spec 009 (de-identification engines on real prose) and spec 010 (a fine-tuned Age/Sex/Date
tagger). Scores: `data/deid/maccrobat_*.csv`; write-up: `docs/deidentification.md`.
