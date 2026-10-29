// The design's SVG charts, fed from the API instead of sample data.
import { Fragment, useState, type MouseEvent, type ReactNode } from "react";
import { fmt, seq } from "../format";

type TipState = { x: number; y: number; content: ReactNode } | null;

function useTip(): [TipState, (e: MouseEvent, c: ReactNode) => void, () => void] {
  const [tip, setTip] = useState<TipState>(null);
  const show = (e: MouseEvent, content: ReactNode) => {
    const r = (e.currentTarget as Element).closest(".chart")!.getBoundingClientRect();
    setTip({ x: e.clientX - r.left, y: e.clientY - r.top, content });
  };
  return [tip, show, () => setTip(null)];
}
const Tip = ({ tip }: { tip: TipState }) => (tip ? <div className="tip" style={{ left: tip.x, top: tip.y }}>{tip.content}</div> : null);

export function HBars({ rows, max = 100, unit = "%", flagAbove }:
  { rows: { k: string; v: number }[]; max?: number; unit?: string; flagAbove?: number }) {
  const [tip, show, hide] = useTip();
  const rowH = 24, labelW = 230, w = 640, plotW = w - labelW - 56;
  const h = rows.length * rowH + 20;
  const ticks = [0, 25, 50, 75, 100].filter(t => t <= max);
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Horizontal bar chart">
        {ticks.map(t => (
          <g key={t} transform={`translate(${labelW + plotW * t / max},0)`}>
            <line y1="0" y2={h - 18} className="grid-line" />
            <text y={h - 4} textAnchor="middle" className="axis-text">{t}{unit}</text>
          </g>
        ))}
        {rows.map((r, i) => {
          const bw = Math.max(0, plotW * r.v / max);
          const flagged = flagAbove != null && r.v > flagAbove;
          return (
            <g key={r.k} transform={`translate(0,${i * rowH + 4})`}
               onMouseMove={e => show(e, <span><b>{r.k}</b> · {fmt(r.v)}{unit}</span>)} onMouseLeave={hide}>
              <rect x="0" y="0" width={w} height={rowH - 4} fill="transparent" />
              <text x={labelW - 10} y="13" textAnchor="end" className="lbl">{r.k}</text>
              <rect x={labelW} y="2" width={bw} height={rowH - 8} fill={flagged ? "var(--crit)" : "var(--accent)"} />
              <text x={labelW + bw + 6} y="13" className="val">{fmt(r.v)}{unit}</text>
            </g>
          );
        })}
        <line x1={labelW} x2={labelW} y1="0" y2={h - 18} className="base" />
      </svg>
      <Tip tip={tip} />
    </div>
  );
}

export function Funnel({ steps, w = 640, labelW = 200 }: { steps: { k: string; n: number }[]; w?: number; labelW?: number }) {
  const [tip, show, hide] = useTip();
  if (!steps.length) return null;
  const max = steps[0].n, rowH = 30, plotW = w - labelW - 60;
  const h = steps.length * rowH;
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Visits at each scale">
        {steps.map((s, i) => {
          const bw = plotW * s.n / max, pct = 100 * s.n / max;
          return (
            <g key={s.k} transform={`translate(0,${i * rowH})`}
               onMouseMove={e => show(e, <span><b>{s.k}</b> · {s.n.toLocaleString()} ({fmt(pct)}% of all visits)</span>)} onMouseLeave={hide}>
              <rect width={w} height={rowH} fill="transparent" />
              <text x={labelW - 10} y="19" textAnchor="end" className="lbl">{s.k}</text>
              <rect x={labelW} y="6" width={bw} height={rowH - 12} fill={i === steps.length - 1 ? "var(--accent-ink)" : "var(--accent)"} opacity={1 - i * 0.12} />
              <text x={labelW + bw + 6} y="19" className="val">{s.n.toLocaleString()}</text>
            </g>
          );
        })}
        <line x1={labelW} x2={labelW} y1="0" y2={h} className="base" />
      </svg>
      <Tip tip={tip} />
    </div>
  );
}

export function ClinicBars({ data, overall, selected, spreadFlag = 8 }:
  { data: { clinic: string; v: number; lo: number; hi: number; n: number }[]; overall: number | null; selected: string; spreadFlag?: number }) {
  const [tip, show, hide] = useTip();
  const w = 640, h = 200, padL = 36, padB = 34, padT = 10, plotW = w - padL - 10, plotH = h - padB - padT;
  const max = 80, n = data.length, slot = plotW / Math.max(1, n), bw = Math.min(40, slot - 8);
  const y = (v: number) => padT + plotH - plotH * Math.min(v, max) / max;
  const vals = data.map(d => d.v);
  const spread = vals.length ? Math.max(...vals) - Math.min(...vals) : 0;
  const ref = overall ?? 0;
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Periodontitis prevalence by clinic">
        {[0, 20, 40, 60, 80].map(t => (
          <g key={t}><line x1={padL} x2={w - 10} y1={y(t)} y2={y(t)} className="grid-line" /><text x={padL - 6} y={y(t) + 4} textAnchor="end" className="axis-text">{t}%</text></g>
        ))}
        {data.map((d, i) => {
          const x = padL + slot * i + (slot - bw) / 2;
          const dev = Math.abs(d.v - ref);
          const dim = selected !== "All" && selected !== d.clinic;
          return (
            <g key={d.clinic} opacity={dim ? 0.35 : 1}
               onMouseMove={e => show(e, <span><b>Clinic {d.clinic}</b> · {fmt(d.v)}% (95% CI {fmt(d.lo)}–{fmt(d.hi)}) · {d.n} people</span>)} onMouseLeave={hide}>
              <rect x={padL + slot * i} y={padT} width={slot} height={plotH} fill="transparent" />
              <rect x={x} y={y(d.v)} width={bw} height={plotH - (y(d.v) - padT)} fill={dev > spreadFlag ? "var(--series-2)" : "var(--accent)"} />
              <line x1={x + bw / 2} x2={x + bw / 2} y1={y(d.hi)} y2={y(d.lo)} stroke="var(--ink)" strokeWidth="1.2" />
              <line x1={x + bw / 2 - 5} x2={x + bw / 2 + 5} y1={y(d.hi)} y2={y(d.hi)} stroke="var(--ink)" strokeWidth="1.2" />
              <line x1={x + bw / 2 - 5} x2={x + bw / 2 + 5} y1={y(d.lo)} y2={y(d.lo)} stroke="var(--ink)" strokeWidth="1.2" />
              <text x={x + bw / 2} y={h - padB + 14} textAnchor="middle" className="axis-text">{d.clinic}</text>
            </g>
          );
        })}
        {overall != null && <>
          <line x1={padL} x2={w - 10} y1={y(overall)} y2={y(overall)} stroke="var(--ink)" strokeWidth="1.5" strokeDasharray="4 3" />
          <text x={w - 12} y={y(overall) - 5} textAnchor="end" className="val">overall {fmt(overall)}%</text>
        </>}
        <line x1={padL} x2={w - 10} y1={y(0)} y2={y(0)} className="base" />
        <text x={padL + plotW / 2} y={h - 4} textAnchor="middle" className="axis-text">Clinic</text>
      </svg>
      <Tip tip={tip} />
      <div className="legend">
        <span><i className="sw" style={{ background: "var(--accent)" }}></i>Within {spreadFlag} pts of overall</span>
        <span><i className="sw" style={{ background: "var(--series-2)" }}></i>More than {spreadFlag} pts from overall</span>
        <span>Whiskers: 95% interval</span>
        <span>Spread {fmt(spread)} pts</span>
      </div>
    </div>
  );
}

export function Matrix({ labels, colLabels, m, flagBelow }:
  { labels: string[]; colLabels?: string[]; m: (number | null)[][]; flagBelow?: number }) {
  const n = labels.length;
  return (
    <div className="matrix" style={{ gridTemplateColumns: `minmax(90px,auto) repeat(${n}, minmax(0,1fr))` }}>
      <div className="h"></div>
      {(colLabels ?? labels).map((l, j) => <div className="h" key={j} title={labels[j]}>{l}</div>)}
      {m.map((row, i) => (
        <Fragment key={i}>
          <div className="rh">{labels[i]}</div>
          {row.map((v, j) => {
            const diag = i === j || v == null;
            const flag = flagBelow != null && !diag && v! < flagBelow;
            return (
              <div key={j} className={`c ${diag ? "diag" : ""} ${flag ? "flag" : ""}`}
                   title={diag ? "" : `${labels[i]} ↔ ${labels[j]}: ${fmt(v)}%`}
                   style={diag ? {} : { background: seq(v! / 100), color: v! / 100 > 0.5 ? "#fff" : "var(--ink)" }}>
                {diag ? "—" : `${fmt(v, 0)}%`}
              </div>
            );
          })}
        </Fragment>
      ))}
    </div>
  );
}

export function TransitionMatrix({ labels, rowPct, count, direction }:
  { labels: string[]; rowPct: number[][]; count: number[][]; direction: (string | null)[][] }) {
  return (
    <div>
      <div className="matrix" style={{ gridTemplateColumns: `minmax(110px,auto) repeat(${labels.length}, minmax(0,1fr))` }}>
        <div className="h" style={{ justifyContent: "flex-start" }}>earlier ↓ / next →</div>
        {labels.map(l => <div className="h" key={l}>{l}</div>)}
        {rowPct.map((row, i) => (
          <Fragment key={i}>
            <div className="rh">{labels[i]}</div>
            {row.map((v, j) => {
              const improved = direction[i][j] === "better" && v > 0;
              const t = v / 100;
              return (
                <div key={j} className={`c ${improved ? "flag" : ""}`}
                     title={`${labels[i]} → ${labels[j]}: ${fmt(v)}% of the row (${count[i][j]} visit pairs)`}
                     style={{ background: seq(t), color: t > 0.5 ? "#fff" : "var(--ink)" }}>{fmt(v, 0)}%</div>
              );
            })}
          </Fragment>
        ))}
      </div>
      <div className="legend" style={{ marginTop: 8 }}>
        <span>Row % of visit pairs with that stage at the earlier visit</span>
        <span><i className="sw" style={{ boxShadow: "inset 0 0 0 2px var(--crit)", background: "transparent" }}></i>Below the diagonal: stage improved (a charting or rule error unless treated)</span>
      </div>
    </div>
  );
}
