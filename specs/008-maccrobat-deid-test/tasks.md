# Tasks: MACCROBAT de-identification test pass

- [x] T001 Spec; source and licence (figshare, CC BY 4.0; Hugging Face BIO mirror pinned to a revision)
- [x] T002 [US1] tests then `maccrobat.bio_spans`: BIO to text and spans, lenient I- tags, approximate spacing
- [x] T003 [US2] tests then `maccrobat.role` and `maccrobat.load_bio`: Safe Harbor date and age rule, clinical types as decoys, duplicates collapsed
- [x] T004 [US3] tests then `deid_eval.damage_by_type`
- [x] T005 `scripts/30_maccrobat_deid.py` (`--download` fetches the pinned file into data/raw/); run the local engines; docs/deidentification.md and docs/data_sources.md
- [x] T006a Presidio (+guard, +regex_v2+guard)
- [ ] T006 Run the transformer engines (hf_stanford, hf_obi) on CPU
- [x] T007 `maccrobat.load_brat`: the original figshare release (exact text and offsets, overlapping entities); default source of the script
