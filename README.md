# Health Transformation Lab

> **Personal learning project.** Built on my own time. "Health Transformation Lab" is a working name for a
> personal idea: not affiliated with or endorsed by any employer, institution or vendor, and nothing here is any
> organization's plan, study or finding. Synthetic data only. See [DISCLAIMER.md](DISCLAIMER.md).

**Better oral health for millions of people, and better overall health where medicine meets dentistry, by
testing in public the AI that reads our records and answers our questions.**

There are two paths in, and each starts with a short pitch and drills down to the detail.

## 1. The dental record (EDR): can software read the chart the way a specialist does?

<a href="docs/edr/full_text_and_notes.md"><img src="docs/img/edr_deck_cover.png" alt="The diagnosis is in the dental record. Nobody can count it." width="480"></a>

Gum disease is written down at almost every dental visit, but in pieces: notes, forms, codes and measurements
that often disagree, so nobody can count it across clinics or link it to diabetes. This study reads the whole
record, compares rules and AI with gum specialists, and runs end to end on **synthetic** records:

- the whole record, combined by rules: **234 of 240** charts right;
- the free-text note alone, read by a small trained model: **219 of 240**;
- a large medical AI used as is: **185 of 240**.

Scored against the generator's truth on synthetic charts, not clinical performance.

| For | Go to |
|---|---|
| **Executives** (11 slides, 10 minutes) | [read the pitch with speaker notes](docs/edr/full_text_and_notes.md) · [slides](docs/edr/deck.html) (download and open in a browser) |
| **Scientists** | [the study](docs/edr/README.md): the seven kinds of evidence, every method with 95% intervals, the acceptance test, models, de-identification |
| **Engineers** | [code walkthrough](docs/code_walkthrough.md), [deployment](docs/deployment.md), [how we work](AGENTS.md) |

## 2. The lab: is AI safe where medicine meets dentistry, and does it help people get care?

<a href="docs/pitch/full_text_and_notes.md"><img src="docs/img/pitch_deck_cover.png" alt="AI passes the dental exam. It fails the real patient." width="480"></a>

AI scores 81% on the dental licensing exam and 22% on real patient cases (GlobalDentBench, 2026), and no public
test checks whether it connects the mouth to the rest of the body or helps people get care. The lab would write
those missing test questions, each traced to published evidence, and measure the gain from an open agent in public.

| For | Go to |
|---|---|
| **Executives** (6 slides, plus backup) | [read the pitch with speaker notes](docs/pitch/full_text_and_notes.md) · [slides](docs/pitch/deck.html) (download and open in a browser) |
| **Detail** | [the pitch's sources and how this repo tests it](docs/pitch/README.md) |

## How the two paths connect

The dental record path builds synthetic patients whose right answers are known, in OMOP, the format medicine
already uses. Those patients become test questions for the lab. One harness, with the same models, runners, harm grades
and leaderboards, scores AI first on gum charts, then on case questions, then on broader medical-dental questions.

## Run it

```bash
cd python && pip install -e ".[dev]"
pytest -q tests                                    # Python tests
cd .. && python/scripts/make_parity_inputs.sh && Rscript r/tests/test_parity.R   # Python and R give the same numbers
python docs/build_decks.py                         # rebuild both decks from docs/<deck>/slides/
```

Ground rules: synthetic data only, never PHI; Python and R in parity; anything simulated is labelled simulated
([AGENTS.md](AGENTS.md)). Open decisions: [action items](docs/action_items.md). Owner John Bowyer · MIT licence.
