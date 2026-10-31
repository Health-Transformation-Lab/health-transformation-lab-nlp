"""The data-dictionary ERD (#379): a third format beside the entity and full views, for reading a source's tables
with their data. Tables sit in titled subject areas. Each table's header gives its name, its row count, what one
row is, and who writes it. Each column row gives the name, the type and meaning, and its profile (nulls, distinct
values, and every value's count when there are few, from table_profile.py), or says it isn't measured yet.

Colours: green header fact table, orange header dimension; name in blue primary key, purple foreign key, red would
hold PHI in a real extract (de-identify), grey not linked; red text an open question or issue. Lines run between the
key rows. Each model declares GROUPS, KINDS, PHI and QUESTIONS beside its TABLES.
Run: python3 silver_erd.py (writes these too), then render with drawio_render.js (render.md).
"""
import math
from pathlib import Path

from gold_erd import CARD, INK, MUTED, Diagram

SRC = Path(__file__).resolve().parent.parent / "silver" / "source"
COLS = (150, 230, 250)                  # name, type and meaning, profile
W = sum(COLS)
LINE, PAD, GAP = 13, 24, 70
FACT, DIM, AREA = "#DFF5D8", "#FBD9A6", "#FDF7C3"
PK, FK, PHI_RED, PLAIN, QUESTION = "#1F5FBF", "#7B3FA0", "#C62828", "#6B7280", "#C62828"
NOT_YET = "not profiled yet"


def _lines(text, width):
    """Lines a wrapped cell needs: about 5.6 px per character at 10 px Helvetica, newlines counted."""
    per = max(1, int((width - 10) / 5.6))
    return sum(max(1, math.ceil(len(part) / per)) for part in text.split("\n"))


def _esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")


def _row_texts(m, table, col, tstats):
    meaning = f"{col.type}; {col.description}"
    question = m.QUESTIONS.get((table, col.name))
    profile = (tstats or {}).get("columns", {}).get(col.name, NOT_YET)
    return meaning, question, profile


def _row_height(meaning, question, profile, name):
    lines = max(_lines(name, COLS[0]), _lines(meaning + ("\n" + question if question else ""), COLS[1]),
                _lines(profile, COLS[2]))
    return lines * LINE + 8


def _table_size(m, name, stats):
    t = m.TABLES[name]
    head = 3 * LINE + _lines(t.description, W) * LINE + 12
    body = sum(_row_height(*_row_texts(m, name, c, stats.get(name)), c.name) for c in t.columns)
    return W, head + body


def _key_role(m, table, col):
    if (table, col.name) in m.PHI:
        return PHI_RED, True
    if "PK" in col.key:
        return PK, True
    if "FK" in col.key:
        return FK, True
    return PLAIN, False


def _draw_table(d, m, name, x, y, stats, cell_ids):
    t, tstats = m.TABLES[name], stats.get(name)
    rows = (tstats or {}).get("rows")
    count = f"{rows:,} rows" if rows is not None else "rows not measured yet"
    head_h = 3 * LINE + _lines(t.description, W) * LINE + 12
    fill = FACT if m.KINDS[name] == "fact" else DIM
    head = (f"<b style='font-size:13px'>{_esc(name)}</b><br>{count}<br>"
            f"<i>{_esc(t.description)}</i><br><span style='color:{MUTED};font-size:9px'>{_esc(t.writer)}</span>")
    hid = d.v(head, x, y, W, head_h, f"rounded=0;fillColor={fill};strokeColor={INK};fontSize=10;fontColor={INK};align=center;verticalAlign=top;")
    cell_ids[(name, None)] = hid
    cy = y + head_h
    for i, col in enumerate(t.columns):
        meaning, question, profile = _row_texts(m, name, col, tstats)
        h = _row_height(meaning, question, profile, col.name)
        band = "#F2F2F2" if i % 2 else "#FFFFFF"
        colour, bold = _key_role(m, name, col)
        base = f"rounded=0;fillColor={band};strokeColor={INK};fontSize=10;align=left;verticalAlign=top;spacingLeft=4;"
        cid = d.v(f"{'<b>' if bold else ''}{_esc(col.name)}{'</b>' if bold else ''}", x, cy, COLS[0], h, base + f"fontColor={colour};")
        cell_ids[(name, col.name)] = cid
        text = _esc(meaning) + (f"<br><span style='color:{QUESTION}'>{_esc(question)}</span>" if question else "")
        d.v(text, x + COLS[0], cy, COLS[1], h, base + f"fontColor={INK};")
        d.v(_esc(profile), x + COLS[0] + COLS[1], cy, COLS[2], h, base + f"fontColor={MUTED if profile == NOT_YET else INK};")
        cy += h


def _legend(d, x, y):
    items = [(FACT, INK, "green header = FACT table (one row per event)"),
             (DIM, INK, "orange header = DIMENSION table (one row per thing)"),
             ("#FFFFFF", PK, "blue name = primary key"),
             ("#FFFFFF", FK, "purple name = foreign key"),
             ("#FFFFFF", PHI_RED, "red name = would hold PHI in a real extract: de-identify"),
             ("#FFFFFF", PLAIN, "grey name = not linked"),
             ("#FFFFFF", QUESTION, "red text in the meaning = an open question or issue"),
             ("#FFFFFF", INK, "profile: null=n (p%); n_distinct=k; value=n (p%), from the data (synthetic)")]
    h = 34 + 22 * len(items)
    d.v("<b>Legend</b>", x, y, 470, h, f"rounded=1;fillColor=#EEF0FA;strokeColor={INK};fontSize=13;verticalAlign=top;")
    for i, (fill, colour, text) in enumerate(items):
        d.v(text, x + 12, y + 30 + 22 * i, 446, 18, f"rounded=0;fillColor={fill};strokeColor={INK};fontSize=10;fontColor={colour};align=left;spacingLeft=4;")
    return h


def build(m, stats=None):
    """m: a model with TABLES, RELATIONSHIPS, GROUPS, KINDS, PHI, QUESTIONS. stats: table_profile.profile() output;
    a table missing from it says its rows aren't measured yet."""
    stats = stats or {}
    d = Diagram()
    legend_h = _legend(d, 10, 10)
    sizes = {n: _table_size(m, n, stats) for n in m.TABLES}
    columns = sorted({c for _, c, _ in m.GROUPS})
    group_w = {title: len(tables) * (W + PAD) + PAD if len(tables) <= 2 else 2 * (W + PAD) + PAD for title, _, tables in m.GROUPS}
    col_w = {c: max(group_w[t] for t, gc, _ in m.GROUPS if gc == c) for c in columns}
    col_x, x = {}, 10
    for c in columns:
        col_x[c] = x
        x += col_w[c] + GAP
    col_y = {c: 10 + legend_h + GAP for c in columns}
    cell_ids = {}
    for title, c, tables in m.GROUPS:
        rows = [tables[i:i + 2] for i in range(0, len(tables), 2)]
        heights = [max(sizes[n][1] for n in row) for row in rows]
        gh = 40 + sum(heights) + PAD * len(rows)
        gx, gy = col_x[c], col_y[c]
        d.v(f"<b>{_esc(title)}</b>", gx, gy, group_w[title], gh,
            f"rounded=1;arcSize=2;fillColor={AREA};strokeColor={INK};fontSize=16;fontColor={INK};verticalAlign=top;")
        ty = gy + 40
        for row, rh in zip(rows, heights):
            tx = gx + PAD
            for n in row:
                _draw_table(d, m, n, tx, ty, stats, cell_ids)
                tx += W + PAD
            ty += rh + PAD
        col_y[c] = gy + gh + GAP
    er = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor={INK};strokeWidth=1.2;endFill=0;startFill=0;"
          f"fontSize=9;fontColor={MUTED};labelBackgroundColor=#FFFFFF;")
    for r in m.RELATIONSHIPS:
        src = cell_ids.get((r.child, r.child_cols[0] if r.child_cols else None)) or cell_ids[(r.child, None)]
        tgt = cell_ids.get((r.parent, r.parent_cols[0] if r.parent_cols else None)) or cell_ids[(r.parent, None)]
        a, b = r.cardinality[:2], r.cardinality[-2:]
        dash = f"dashed=1;dashPattern=6 4;strokeColor={MUTED};" if r.derived else ""
        d.e(src, tgt, er + dash + f"startArrow={CARD[b]};endArrow={CARD[a]};", r.label if r.derived else "")
    return d


def write(prefix, m, stats=None):
    SRC.mkdir(parents=True, exist_ok=True)
    stem = f"{prefix}_dictionary"
    (SRC / f"{stem}.drawio").write_text(build(m, stats).xml(stem))
    return SRC / f"{stem}.drawio"

