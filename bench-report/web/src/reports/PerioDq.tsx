// PerioBench · EHR data quality: the Perio Data Quality (DQ) Monitor design on the gold tables.
import { useMemo, useState } from "react";
import type { PerioDq as Payload } from "../api";
import { ClinicBars, Funnel, HBars, Matrix, TransitionMatrix } from "../components/charts";
import { Panel, SectionH, Tile } from "../components/ui";
import { clinicName, columnName, fmt } from "../format";

const SHORT: Record<string, string> = {
  notes: "Note", exam_form: "Exam", proc_codes_completed: "Proc. done", proc_codes_planned: "Proc. planned",
  proc_dx_completed: "Dx done", proc_dx_planned: "Dx planned", probing_chart: "Gum meas.", radiograph_ai: "X-ray AI",
};
const CHECK_PILL: Record<string, string> = { PASS: "good", FAIL: "crit", REPORT: "neutral" };

export default function PerioDq({ data }: { data: Payload }) {
  const [clinic, setClinic] = useState("All");
  const tiles = data.tiles[clinic];
  const scope = clinic === "All" ? "all clinics" : clinicName(clinic).toLowerCase();
  const th = data.thresholds;

  const accuracy = data.accuracy.filter(a => a.clinic === clinic);
  const checks = data.checks.filter(c => c.clinic === clinic);
  const funnel = useMemo(() => data.scales.filter(s => s.method === "algorithm_design")
    .map(s => ({ k: s.scale_label, n: s.visit_count })), [data]);
  const scaleMethods = useMemo(() => [...new Set(data.scales.map(s => s.method))], [data]);
  const scaleNames = useMemo(() => [...new Set(data.scales.map(s => s.scale_label))], [data]);
  const loaded = data.provenance.loaded_ts ? data.provenance.loaded_ts.slice(0, 10) : "unknown";

  return (
    <>
      <header className="top">
        <div>
          <h1>{data.title}</h1>
          <div className="sub">{data.bench_name} · data quality of electronic dental records for finding gum disease (periodontal phenotyping) · Zozus framework with Kahn and Liaw extensions</div>
        </div>
        <div className="meta">
          <span className="chip sample">Synthetic data · scored against the generator's truth</span>
          <span className="chip">{data.provenance.visit_count.toLocaleString()} visits</span>
          <span className="chip">{data.provenance.clinic_count} clinics</span>
          <span className="chip" title={data.gold_schema}>loaded {loaded}</span>
          {data.provenance.git_commit_sha && <span className="chip" title="git commit of the results">{data.provenance.git_commit_sha.slice(0, 7)}</span>}
          <span className="chip">{data.source === "databricks" ? "Databricks" : "snapshot"}</span>
        </div>
      </header>

      <p className="banner"><b>Not clinical performance.</b> Every visit is synthetic, from the study's generator, and the
        "truth" is the generator's own. A low score points at records to recheck: usually a coding or charting gap, never a
        judgment that a dentist got it wrong.</p>

      <div className="rail" role="toolbar" aria-label="Filters">
        <label className="field">Clinic
          <select value={clinic} onChange={e => setClinic(e.target.value)} aria-label="Clinic">
            {data.clinics.map(c => <option key={c} value={c}>{clinicName(c)}</option>)}
          </select>
        </label>
        <span className="field">Completeness, accuracy and checks follow the clinic; consistency and temporal plausibility are for all clinics.</span>
      </div>

      <div className="tiles">
        <Tile eyebrow="Zozus" domain="Completeness" tile={tiles.completeness}
              def={`Visits with exam form, diagnosis codes and gum measurements all present, ${scope}`} />
        <Tile eyebrow="Zozus" domain="Accuracy" tile={tiles.accuracy}
              def={`Rules on the whole record, measurements first (v0), against the truth, ${scope}. Exam form first: ${fmt(tiles.accuracy.design_value)}%`} />
        <Tile eyebrow="Zozus" domain="Consistency" tile={tiles.consistency}
              def="Spread of periodontitis prevalence across clinics (design rules). Smaller is steadier" />
        <Tile eyebrow="Kahn" domain="Temporal plausibility" tile={tiles.temporal}
              def="Visit pairs, no treatment between, whose stage improved (design rules). Lower is better" />
        <Tile eyebrow="Liaw" domain="Reliability" tile={tiles.reliability}
              def="Needs real reviewers to label charts; simulated reviewers are a dry run" />
      </div>

      <div className="grid">
        <SectionH src="Zozus · completeness">Completeness</SectionH>

        <Panel w="w8" eyebrow="Column data value completeness" title="Missing by evidence column" rung="dq_column_missing"
               note={`Share of all ${data.provenance.visit_count.toLocaleString()} visits where the column is empty. Columns above 30% are flagged.`}>
          <HBars rows={data.missingness.map(m => ({ k: columnName(m.column), v: m.missing_pct }))} flagAbove={30} />
        </Panel>

        <Panel w="w4" eyebrow="Row data value completeness" title="Visits at each scale" rung="dq_prevalence"
               note="All visits; complete cases (every evidence source present); the reference set reviewers label.">
          <Funnel steps={funnel} w={360} labelW={112} />
        </Panel>

        <Panel w="w12" eyebrow="Conformance, completeness and plausibility" title={`Checks · ${clinicName(clinic)}`} rung="dq_check"
               note="PASS: no failures allowed and none found. REPORT: a rate to read, with no pass mark.">
          <div className="twrap"><table>
            <thead><tr><th>Category</th><th>Check</th><th className="num">Checked</th><th className="num">Failed</th><th className="num">Pass</th><th>Status</th></tr></thead>
            <tbody>{checks.map(c => (
              <tr key={c.check}><td>{c.category}</td><td className="k"><code>{c.check.split(":")[1] ?? c.check}</code></td>
                <td className="num">{c.checked_count.toLocaleString()}</td><td className="num">{c.failed_count.toLocaleString()}</td>
                <td className="num">{fmt(c.pass_pct, 1)}%</td>
                <td><span className={`pill ${CHECK_PILL[c.status] ?? "neutral"}`} style={{ marginTop: 0 }}>{c.status}</span></td></tr>
            ))}</tbody>
          </table></div>
        </Panel>

        <SectionH src="Hierarchy: truth → independent measurement → aggregate statistics">Accuracy</SectionH>

        <Panel w="w6" eyebrow="Comparison to truth" title={`Each evidence source against the truth · ${clinicName(clinic)}`} rung="fact_visit_evidence"
               note="Answered: visits the source gives a status for. Agrees: of those, the share matching the generator's truth (six statuses).">
          <div className="twrap"><table>
            <thead><tr><th>Evidence source</th><th className="num">Answered</th><th className="num">Agrees with truth</th></tr></thead>
            <tbody>{accuracy.map(a => (
              <tr key={a.source}><td className="k">{a.source_label}</td><td className="num">{fmt(a.answered_pct)}%</td><td className="num">{fmt(a.agree_pct)}%</td></tr>
            ))}</tbody>
          </table></div>
        </Panel>

        <Panel w="w6" eyebrow="Comparison to independent measurement" title="Concordance between sources" rung="dq_source_concordance"
               note="Pairwise agreement on status where both answer, truth excluded, all clinics. Pairs under 65% are outlined.">
          <Matrix labels={data.concordance.labels} colLabels={data.concordance.methods.map(m => SHORT[m] ?? m)}
                  m={data.concordance.agree_pct} flagBelow={65} />
        </Panel>

        <SectionH src="Zozus · stratified by clinic">Consistency</SectionH>

        <Panel w="w8" eyebrow="Site consistency" title="Periodontitis prevalence by clinic" rung="dq_prevalence"
               note="Design rules, people per clinic. Differences are not errors by themselves: large gaps are worth a look as possible population or documentation effects.">
          <ClinicBars selected={clinic} overall={data.prevalence.overall_pct}
                      data={data.prevalence.clinics.map(c => ({ clinic: c.clinic, v: c.periodontitis_pct, lo: c.ci_low_pct, hi: c.ci_high_pct, n: c.person_count }))} />
        </Panel>

        <Panel w="w4" eyebrow="By scale" title="Periodontitis at each scale" rung="dq_prevalence"
               note="Share of visits with periodontitis, by method and scale. A steady share across scales means the complete cases and the reference set look like everyone.">
          <div className="twrap"><table>
            <thead><tr><th>Method</th>{scaleNames.map(n => <th key={n} className="num">{n}</th>)}</tr></thead>
            <tbody>{scaleMethods.map(m => (
              <tr key={m}><td className="k">{data.scales.find(s => s.method === m)!.method_label}</td>
                {scaleNames.map(n => {
                  const s = data.scales.find(x => x.method === m && x.scale_label === n);
                  return <td key={n} className="num" title={s ? `${s.visit_count.toLocaleString()} visits; stage III–IV ${fmt(s.stage3_4_pct)}%` : ""}>{s ? `${fmt(s.periodontitis_pct)}%` : "—"}</td>;
                })}</tr>
            ))}</tbody>
          </table></div>
          <p className="note">Hover a cell for its visits and stage III–IV share.</p>
        </Panel>

        <SectionH src="Borrowed from Kahn et al. · Liaw et al.">Concepts from other frameworks</SectionH>

        <Panel w="w6" eyebrow="Temporal plausibility" title="Stage at one visit and the next" rung="Kahn · dq_stage_transition"
               note="Design rules, visit pairs with no treatment between. Without periodontal therapy a stage should hold or worsen.">
          <TransitionMatrix labels={data.transitions.labels} rowPct={data.transitions.row_pct}
                            count={data.transitions.count} direction={data.transitions.direction} />
        </Panel>

        <Panel w="w6" eyebrow="Temporal plausibility" title="Implausible change by method" rung="Kahn · dq_temporal_change"
               note="Share of visit pairs whose stage improved. Lower is more plausible.">
          <HBars rows={data.temporal.map(t => ({ k: t.method_label, v: t.improved_pct }))} max={25} flagAbove={th.temporal?.watch} />
          {data.injected && (
            <dl className="kv" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
              <dt>Charting errors injected (synthetic only)</dt><dd>{data.injected.injected_count}</dd>
              <dt>Caught by the temporal checks</dt><dd>{fmt(data.injected.caught_pct)}%</dd>
              <dt>Flagged without an error</dt><dd>{fmt(data.injected.false_flag_pct, 2)}%</dd>
            </dl>
          )}
        </Panel>

        <Panel w="w12" eyebrow="Reliability" title="Not assessed yet" rung="Liaw · reliability">
          <p className="note">Reliability needs real reviewers labelling the same charts (agreement between reviewers, and the
            intra-class correlation of attachment loss by site, tooth and patient). Simulated reviewers are a dry run, so
            nothing is shown here until real labels exist.</p>
        </Panel>
      </div>

      <p className="foot">Read from <code>{data.gold_schema}</code> · generated {data.generated_ts}{data.cached ? " (cached)" : ""}.
        Tile thresholds are starting points, not agreed targets: completeness ≥ {th.completeness.good}% within target, ≥ {th.completeness.watch}% watch;
        accuracy ≥ {th.accuracy.good}% / ≥ {th.accuracy.watch}%; consistency ≤ {th.consistency.good} / ≤ {th.consistency.watch} pts;
        temporal ≤ {th.temporal.good}% / ≤ {th.temporal.watch}%. The same measures as the EHR DQ grader dashboard in Databricks. Hover any bar or cell for its value.</p>
    </>
  );
}
