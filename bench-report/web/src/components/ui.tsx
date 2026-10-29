import type { ReactNode } from "react";
import { fmt } from "../format";
import type { Pill, Tile as TileData } from "../api";

export const STATUS_LABEL: Record<Pill, string> = {
  good: "Within target", warn: "Watch", crit: "Needs attention", none: "Not assessed",
};

export function Tile({ eyebrow, domain, tile, def }: { eyebrow: string; domain: string; tile: TileData; def: string }) {
  const cls = tile.status === "none" ? "" : tile.status;
  return (
    <div className={`tile ${cls}`} data-testid={`tile-${domain}`}>
      <div className="eyebrow">{eyebrow}</div>
      <div className="domain">{domain}</div>
      <div className="value">{tile.value == null ? "—" : fmt(tile.value)}<small>{tile.unit}</small></div>
      <div className="def">{def}</div>
      <span className={`pill ${cls}`} style={tile.status === "none" ? { color: "var(--ink-3)", background: "var(--surface-2)" } : {}}>
        {STATUS_LABEL[tile.status]}
      </span>
    </div>
  );
}

export function Panel({ eyebrow, title, rung, w, note, children }:
  { eyebrow: string; title: string; rung?: string; w?: string; note?: ReactNode; children?: ReactNode }) {
  return (
    <section className={`panel ${w ?? ""}`}>
      <div className="phead">
        <div><div className="eyebrow">{eyebrow}</div><h2>{title}</h2></div>
        {rung && <span className="rung">{rung}</span>}
      </div>
      {note && <p className="note">{note}</p>}
      {children}
    </section>
  );
}

export const SectionH = ({ children, src }: { children: ReactNode; src?: ReactNode }) => (
  <div className="section-h"><h3>{children}</h3><div className="line"></div>{src && <span className="src">{src}</span>}</div>
);
