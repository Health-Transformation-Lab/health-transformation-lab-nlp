"""Build the pitch deck from its slide sources: docs/pitch/slides/NN-<id>.html, one <section> per slide with the
speaker notes in its <aside>. Writes deck.html (slides scaled to the window, notes under each) and
full_text_and_notes.md (every slide's text and notes, for reading or search).

    python docs/pitch/build.py
"""

import html
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "Health Transformation Lab: Shark Tank pitch"
HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&display=swap"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400..700&display=swap"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Caveat:wght@500..700&display=swap">
<style>body{{margin:0;background:#2b2b2b;font-family:Arial,sans-serif}}*{{box-sizing:border-box;margin:0}}
.wrap{{width:min(96vw,1280px);aspect-ratio:16/9;margin:24px auto 0;overflow:hidden;position:relative}}
.frame{{width:1920px;height:1080px;transform-origin:0 0;position:absolute}}.frame>section{{width:1920px;height:1080px;position:relative}}
.notes{{width:min(96vw,1280px);margin:0 auto 32px;background:#f4f1ea;padding:16px 20px;font-size:15px;line-height:1.5;color:#222}}
.disclaimer{{width:min(96vw,1280px);margin:24px auto 0;color:#ddd;font-size:14px;line-height:1.5}}
td,th{{padding:12px 16px;border-bottom:1px solid #D9D3C4}}ul{{padding-left:1.2em}}</style></head><body>
<p class="disclaimer">A personal idea, not affiliated with or endorsed by any organization. Figures are cited on each slide; nothing marked "to measure" has been measured.</p>
"""
TAIL = """<script>function f(){document.querySelectorAll('.wrap').forEach(w=>w.firstChild.style.transform='scale('+w.clientWidth/1920+')')}addEventListener('resize',f);f()</script></body></html>
"""


def slides():
    for path in sorted((HERE / "slides").glob("[0-9][0-9]-*.html")):
        src = path.read_text(encoding="utf-8")
        notes = re.search(r"<aside>(.*?)</aside>", src, re.S)
        yield path.stem.split("-", 1)[1], re.sub(r"\s*<aside>.*?</aside>", "", src, flags=re.S), \
            notes.group(1).strip() if notes else ""


def visible_text(section: str) -> list[str]:
    section = re.sub(r"<svg.*?</svg>", "", section, flags=re.S)
    parts = (html.unescape(p).strip() for p in re.split(r"<[^>]+>", section))
    return [p for p in parts if p]


def main():
    deck, md = [HEAD.format(title=TITLE)], [f"# {TITLE}: full text and notes\n",
        "A personal idea, not affiliated with or endorsed by any organization. Built from `slides/` by `build.py`; "
        "edit the slides, then rebuild.\n"]
    for n, (sid, section, notes) in enumerate(slides(), 1):
        deck.append(f'<div class="wrap"><div class="frame">{section}</div></div>'
                    f'<div class="notes"><b>Slide {n} notes:</b> {notes}</div>\n')
        md.append(f"\n## Slide {n} — {sid}\n\n" + "\n".join(visible_text(section)) + "\n")
        if notes:
            md.append(f"\n**Speaker notes:** {html.unescape(notes)}\n")
    deck.append(TAIL)
    (HERE / "deck.html").write_text("".join(deck), encoding="utf-8")
    (HERE / "full_text_and_notes.md").write_text("".join(md), encoding="utf-8")
    print(f"built {n} slides: deck.html, full_text_and_notes.md")


if __name__ == "__main__":
    main()
