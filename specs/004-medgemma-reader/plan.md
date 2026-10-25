# Plan: MedGemma reader

## Constitution check

| Principle | How |
|---|---|
| 0 Personal, not affiliated | Exploratory banner; Google described only from public sources |
| I Synthetic only | Reader runs the residual PHI scan before sending a note; synthetic notes only |
| II Two languages | No new metric; predictions use the existing CSV contract read by R |
| III Test-first | `tests/test_llm_reader.py` written before `llm_reader.py` |
| IV Honest outputs | Simulated backend writes `simulated_*` files and `sim:` methods; costs ILLUSTRATIVE |
| V Published evidence | AAP/EFP criteria shared with the judge prompt |
| VI Simple, seeded | Few-shot choice and simulator seeded; stdlib HTTP client; transformers/peft optional extras |

## Design

- `judge.CRITERIA`: status definitions and rules, shared by the judge and reader prompts (judge prompt text unchanged).
- `llm_reader.py`
  - `build_messages(note, examples, variant)` → chat messages
  - `parse_answer(raw, note)` → dict + gate result
  - backends: `HFChat` (transformers; multimodal 4B via `AutoModelForImageTextToText`, text 27B via `AutoModelForCausalLM`; optional LoRA adapter), `OpenAIChat` (stdlib), `SimulatedReader`
  - `LLMReader(model_entry, backend, shots, variant)` with `fit`/`predict` like other rungs, plus `.details`
  - `sft_records(train)` for fine-tuning
- `registry`: `family`, `modality` fields; `families_of(reg, methods)`.
- Scripts: `11_ai_predict.py --backend/--shots/--variant/--limit`; `15_judge.py` auto family exclusion; `17_medgemma_lora.py`.
- Notebook `databricks/notebooks/03_medgemma_reader.py`.
- Extras: `.[llm]` (torch, transformers ≥ 4.50, accelerate), `.[lora]` (peft, trl, datasets).
