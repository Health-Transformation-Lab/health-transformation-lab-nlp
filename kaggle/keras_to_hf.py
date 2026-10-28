"""Turn MedGemma from Kaggle Models into a local transformers folder, so the Kaggle notebook needs no Hugging
Face token (a notebook pushed by `kaggle kernels push` can't read Kaggle Secrets).

Kaggle hosts MedGemma only as a Keras-Hub preset (keras/medgemma, float32 .h5). keras-hub's exporter writes
weights and tokenizer, and finish() puts in what it gets wrong or leaves out: Google's own config.json and
generation_config.json for the rung (the exporter's config is in transformers-5 style, so 4.x would drop the
rope scaling, and it has no stop tokens) and MedGemma's chat template. Saved as bfloat16, the dtype Google
publishes (the Keras float32 weights are bfloat16 values, so nothing is lost); llm_reader still picks the
compute dtype for the GPU (float32 on T4 x2). Checked against google/medgemma-1.5-4b-it: identical weights
and identical prompt token ids. Needs transformers >= 4.52 (the exporter's weight names).

    python kaggle/keras_to_hf.py --rung medgemma-1.5-4b-it --out /kaggle/temp/medgemma-hf
    python scripts/11_ai_predict.py --rung medgemma-1.5-4b-it --backend hf --weights /kaggle/temp/medgemma-hf

On Kaggle the model is attached by kernel-metadata.json's model_sources (kaggle/prepare_kernel.py) and
kagglehub returns its /kaggle/input path; elsewhere kagglehub downloads it (Kaggle API credentials).
"""

import argparse
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "gemma3_chat_template.jinja"   # chat_template.jinja of google/medgemma-1.5-4b-it
CONFIGS = HERE / "hf_config"                     # <rung>.config.json, <rung>.generation_config.json from google/<rung>


def kaggle_handle(rung: str) -> str:
    """The rung's Kaggle Models handle (`kaggle:` in models.yaml)."""
    import yaml
    reg = yaml.safe_load((HERE.parent / "models.yaml").read_text())
    entry = next((m for m in reg["models"] if m["id"] == rung), None)
    if not entry or not entry.get("kaggle") or not (CONFIGS / f"{rung}.config.json").exists():
        raise SystemExit(f"{rung} has no kaggle model handle in models.yaml (and Google's config in "
                         "kaggle/hf_config), so it can't run on Kaggle")
    return entry["kaggle"]


def finish(out: Path, rung: str) -> None:
    """Replace the exported configs with Google's and add MedGemma's chat template (tokenizer and processor)."""
    out = Path(out)
    for name in ("config.json", "generation_config.json"):
        (out / name).write_text((CONFIGS / f"{rung}.{name}").read_text())
    template = TEMPLATE.read_text()
    tok = json.loads((out / "tokenizer_config.json").read_text())
    tok["chat_template"] = template
    (out / "tokenizer_config.json").write_text(json.dumps(tok, indent=2))
    (out / "chat_template.jinja").write_text(template)
    (out / "chat_template.json").write_text(json.dumps({"chat_template": template}, indent=2))


RENAMED = {"is_vision_model": "has_vision_tokens"}   # keras-hub renamed it; MedGemma 4B v1's preset (Oct 2025) has the old one


def _rename(v):
    if isinstance(v, dict):
        return {RENAMED.get(k, k): _rename(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_rename(x) for x in v]
    return v


def compatible_preset(preset: Path, work: Path) -> Path:
    """The preset itself, or, for an older one with renamed config keys, a copy in `work` that keras-hub 0.32 reads:
    its JSON configs rewritten, everything else (the weights) linked. The attached input is never changed."""
    preset, work = Path(preset), Path(work)
    configs = sorted(preset.glob("*.json"))
    if not any(k in p.read_text() for p in configs for k in RENAMED):
        return preset
    work.mkdir(parents=True, exist_ok=True)
    for item in preset.iterdir():
        target = work / item.name
        if item.suffix == ".json":
            target.write_text(json.dumps(_rename(json.loads(item.read_text())), indent=2))
        elif not target.exists():
            target.symlink_to(item.resolve(), target_is_directory=item.is_dir())
    print(f"preset uses older config names {sorted(RENAMED)}: reading a renamed copy in {work}", flush=True)
    return work


def convert(rung: str, out: Path, dtype: str = "bfloat16") -> None:  # pragma: no cover - needs the weights
    os.environ.setdefault("KERAS_BACKEND", "torch")   # before keras is imported; the torch writer streams to disk
    import kagglehub
    import keras_hub

    handle = kaggle_handle(rung)
    preset = compatible_preset(kagglehub.model_download(handle), Path(out).with_name(Path(out).name + "-preset"))
    print(f"converting {handle} ({preset}) to {out} as {dtype}", flush=True)
    model = keras_hub.models.Gemma3CausalLM.from_preset(preset, dtype=dtype)
    model.export_to_transformers(str(out))
    finish(out, rung)
    print(f"wrote {out}", flush=True)


def main() -> None:  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--rung", default="medgemma-1.5-4b-it")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--dtype", default="bfloat16")
    a = ap.parse_args()
    if (a.out / "model.safetensors").exists():
        print(f"{a.out} already converted", flush=True)
        return
    convert(a.rung, a.out, a.dtype)


if __name__ == "__main__":
    main()
