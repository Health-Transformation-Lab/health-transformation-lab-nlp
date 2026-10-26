# Tasks: MACCROBAT de-identification test pass

- [x] T001 Spec; source and licence (figshare, CC BY 4.0; Hugging Face BIO mirror pinned to a revision)
- [x] T002 [US1] tests then `maccrobat.bio_spans`: BIO to text and spans, lenient I- tags, approximate spacing
- [x] T003 [US2] tests then `maccrobat.role` and `maccrobat.load_bio`: Safe Harbor date and age rule, clinical types as decoys, duplicates collapsed
- [x] T004 [US3] tests then `deid_eval.damage_by_type`
- [x] T005 `scripts/32_maccrobat_deid.py` (`--download` re-fetches the original from figshare, MD5 checked); run the local engines; docs/deidentification.md and docs/data_sources.md
- [x] T006a Presidio (+guard, +regex_v2+guard)
- [x] T006 Run the transformer engines (hf_stanford, hf_obi, with regex_v2+guard and with Presidio) on CPU
- [x] T007 `maccrobat.load_brat`: the original figshare release (exact text and offsets, overlapping entities); default source of the script
- [ ] T008 Add a month-year date shape to regex_v2, checked on a set it wasn't tuned on
- [ ] T009 Medical terms in the guard (eponyms, vertebrae and ECG leads, mg/m2, "daily") if Presidio stays in an ensemble
- [x] T010 Commit the dataset under data/external/maccrobat/ with a README (constitution v1.2.0)
