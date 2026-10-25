"""Render .drawio → .png with draw.io's own export page (the engine behind the official export server)."""
import sys, json, asyncio
from pathlib import Path
from playwright.async_api import async_playwright

EXPORT = Path(__file__).parent / "drawio/src/main/webapp/export3.html"   # see render.md

async def main(files, scale=2):
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
        for f in files:
            f = Path(f); xml = f.read_text()
            await pg.goto("http://localhost:8765/export3.html")
            await pg.wait_for_function("typeof render === 'function'", timeout=60000)
            await pg.add_script_tag(url="http://localhost:8765/js/stencils.min.js")
            await pg.add_script_tag(url="http://localhost:8765/js/shapes-14-6-5.min.js")
            await pg.wait_for_function("typeof mxStencilRegistry.loadStencil === 'function'", timeout=60000)
            await pg.evaluate("d => render(d)", {"xml": xml, "format": "png", "scale": scale, "border": 20, "bg": "#ffffff"})
            await pg.wait_for_selector("#LoadingComplete", state="attached", timeout=60000)
            bounds = json.loads(await pg.evaluate("document.getElementById('LoadingComplete').getAttribute('bounds')"))
            await pg.set_viewport_size({"width": int(bounds["width"] + 2 * 20 * scale) + 2, "height": int(bounds["height"] + 2 * 20 * scale) + 2})
            await pg.screenshot(path=str(f.with_suffix(".png")), full_page=True)
            print(f.with_suffix(".png").name, bounds)
        await b.close()

asyncio.run(main(sys.argv[1:]))
