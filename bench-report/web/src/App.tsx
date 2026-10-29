import { useEffect, useState, type ComponentType } from "react";
import { fetchBenches, fetchReport, type Bench } from "./api";
import { Panel } from "./components/ui";
import PerioDq from "./reports/PerioDq";

// "<bench>/<report>" -> the component that draws its payload; a bench's new report adds one line here
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const VIEWS: Record<string, ComponentType<{ data: any }>> = { "perio_bench/dq": PerioDq };

function useHash(): [string, (h: string) => void] {
  const [hash, setHash] = useState(() => window.location.hash.replace(/^#\/?/, ""));
  useEffect(() => {
    const on = () => setHash(window.location.hash.replace(/^#\/?/, ""));
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return [hash, (h: string) => { window.location.hash = `/${h}`; }];
}

export default function App() {
  const [benches, setBenches] = useState<Bench[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hash, go] = useHash();

  useEffect(() => { fetchBenches().then(setBenches, e => setError(String(e.message ?? e))); }, []);
  if (error) return <p className="state err">Could not load the benches: {error}</p>;
  if (!benches) return <p className="state">Loading…</p>;

  const [benchKey, reportKey] = hash.split("/");
  const bench = benches.find(b => b.key === benchKey) ?? benches.find(b => b.reports.length) ?? benches[0];
  const report = bench.reports.find(r => r.key === reportKey) ?? bench.reports[0];

  return (
    <>
      <nav className="rail" aria-label="Benches">
        <div className="tabs" role="tablist" aria-label="Bench">
          {benches.map(b => (
            <button key={b.key} role="tab" aria-selected={b.key === bench.key}
                    onClick={() => go(b.reports.length ? `${b.key}/${b.reports[0].key}` : b.key)}>
              {b.name}{b.status !== "live" && <span className="soon">{b.status}</span>}
            </button>
          ))}
        </div>
        {bench.reports.length > 1 && (
          <div className="scope" role="group" aria-label="Report">
            {bench.reports.map(r => (
              <button key={r.key} aria-pressed={r.key === report?.key} onClick={() => go(`${bench.key}/${r.key}`)}>{r.title}</button>
            ))}
          </div>
        )}
      </nav>
      {report ? <ReportView key={`${bench.key}/${report.key}`} bench={bench.key} report={report.key} /> : <NoReport bench={bench} />}
    </>
  );
}

function ReportView({ bench, report }: { bench: string; report: string }) {
  const [data, setData] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { fetchReport(bench, report).then(setData, e => setError(String(e.message ?? e))); }, [bench, report]);
  const View = VIEWS[`${bench}/${report}`];
  if (error) return <p className="state err">The report could not be built: {error}</p>;
  if (!data) return <p className="state">Querying the gold tables… a stopped SQL warehouse takes a few seconds to start.</p>;
  if (!View) return <p className="state err">No view for {bench}/{report} in this front end.</p>;
  return <View data={data} />;
}

function NoReport({ bench }: { bench: Bench }) {
  return (
    <div className="grid">
      <Panel w="w12" eyebrow={bench.tagline} title={bench.name} rung={bench.status}>
        <div className="bench-card">
          <p className="note">{bench.summary}</p>
          <p className="note">No report yet: <span className="status-tag">{bench.status}</span>. Its tables will live in{" "}
            <code>{bench.gold_schema}</code>, which is empty until {bench.name} has a pipeline.</p>
        </div>
      </Panel>
    </div>
  );
}
