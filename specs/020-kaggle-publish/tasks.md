# Tasks: spec 020

- [x] T001 Tests for the dataset builder and workflow (`test_kaggle_publish.py`), written first
- [x] T002 `kaggle/publish.py` and the cards `kaggle/cards/notes.md`, `results.md` (US1 #120, US2 #121)
- [x] T003 `kaggle-publish.yml`: create public, then version with the commit
- [x] T004 `kaggle/README.md` with the collection steps (US4 #123)
- [x] T005 Run the workflow; check both pages on Kaggle (run 40781230812, 2026-10-28: both datasets public, CC BY 4.0)
- [x] T006 US3 #122: the encoder notebook keeps a rung's weights (`SAVE_MODEL`, `11_ai_predict.py --save-model`); `publish_model.py` and `cards/model.md`; the workflow publishes after a full run (`test_kaggle_model.py`)
- [x] T007 Run the encoder workflow with `save_model` `modernbert-base+cw`, `limit` 0; check the model page on Kaggle (run 40763974247, 2026-10-28: public, instance `modernbert-base-cw` v1, Apache 2.0)
