# Rendering the diagrams

Same tooling as `milliman-panel-notes`.

**draw.io** (`../*.drawio`): `build_drawio.py` writes them from Python (helpers in
`_helpers.py`, Databricks icons in `dbx_icons/`, MIT, from
oieduardorabelo/databricks-architecture-icons). Open in draw.io / diagrams.net to edit,
or export there (File › Export as › PNG). `render_drawio.py` renders them headless with
draw.io's own export page, the engine behind the official export server:

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/jgraph/drawio.git && cd drawio && git sparse-checkout set src/main/webapp && cd ..
(cd drawio/src/main/webapp && python3 -m http.server 8765 &)      # the export page loads its icon bundle over http
pip install playwright && playwright install chromium
python3 build_drawio.py && python3 render_drawio.py ../*.drawio
```

**Process flows** (`../flows/*.mmd`): Mermaid, rendered with the Mermaid CLI:
`mmdc -i 01_run_order.mmd -o 01_run_order.png -s 2 -b white`.

PNGs next to each source were rendered this way at 2×.
