"""Build the folder `kaggle kernels push` sends: the MedGemma notebook with its settings filled in, and
kernel-metadata.json (GPU and internet on; public, since it holds synthetic notes only and no token; MedGemma
attached from Kaggle Models via model_sources). Used by .github/workflows/kaggle-medgemma.yml.

    python kaggle/prepare_kernel.py --out build/kernel --username <kaggle user> [--rung ...] [--limit 10]
        [--shots 0] [--branch main] [--commit <sha>]

--limit 0 reads all 240 review notes (FULL_RUN); any other number reads that many as a test. No Hugging Face
token: a pushed notebook can't read Kaggle Secrets, so the rung's `kaggle:` model (models.yaml) is attached
instead and kaggle/keras_to_hf.py converts it on Kaggle.
"""

import argparse
import json
import re
from pathlib import Path

from keras_to_hf import kaggle_handle

HERE = Path(__file__).resolve().parent
SLUG = "dental-omop-medgemma-reader"
TITLE = "dental omop medgemma reader"          # Kaggle derives the slug from the title: keep them in step


def settings(source: str, rung: str, shots: int, limit: int, branch: str, commit: str = "") -> str:
    """Rewrite the assignments in the notebook's settings cell; fail if one is missing."""
    values = {"RUNG": json.dumps(rung), "SHOTS": str(shots), "TEST_NOTES": str(limit or 10),
              "BRANCH": json.dumps(branch), "COMMIT": json.dumps(commit), "FULL_RUN": str(limit == 0)}
    for name, value in values.items():
        source, n = re.subn(rf"^{name} = [^#\n]*?(\s*(#.*)?)$", rf"{name} = {value}\1", source, flags=re.M)
        if n != 1:
            raise SystemExit(f"settings cell has no single '{name} = ' line")
    return source


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--username", required=True)
    ap.add_argument("--rung", default="medgemma-1.5-4b-it")
    ap.add_argument("--shots", type=int, default=0)
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--branch", default="main")
    ap.add_argument("--commit", default="", help="check out this commit of --branch (empty: its tip)")
    a = ap.parse_args()
    model = kaggle_handle(a.rung)

    nb = json.loads((HERE / "medgemma_reader.ipynb").read_text())
    cell = next(c for c in nb["cells"] if c["cell_type"] == "code" and "RUNG =" in "".join(c["source"]))
    cell["source"] = settings("".join(cell["source"]), a.rung, a.shots, a.limit, a.branch, a.commit).splitlines(keepends=True)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "medgemma_reader.ipynb").write_text(json.dumps(nb, indent=1) + "\n")
    meta = {"id": f"{a.username}/{SLUG}", "title": TITLE, "code_file": "medgemma_reader.ipynb",
            "language": "python", "kernel_type": "notebook", "is_private": False, "enable_gpu": True,
            "enable_tpu": False, "enable_internet": True, "dataset_sources": [], "competition_sources": [],
            "kernel_sources": [], "model_sources": [model]}
    (a.out / "kernel-metadata.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(f"prepared {meta['id']}: rung={a.rung} ({model}) shots={a.shots} "
          f"{'all 240 notes' if a.limit == 0 else f'{a.limit} notes'} from branch {a.branch}"
          f"{f' at {a.commit[:12]}' if a.commit else ''}")


if __name__ == "__main__":
    main()
