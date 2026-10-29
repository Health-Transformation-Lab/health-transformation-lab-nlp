// The API's payloads (bench_report/main.py, reports/perio_dq.py). Synthetic data only.

export type BenchStatus = "live" | "planned" | "exploratory";
export type Pill = "good" | "warn" | "crit" | "none";

export interface ReportInfo { key: string; title: string; summary: string }
export interface Bench {
  key: string; name: string; tagline: string; summary: string; status: BenchStatus; gold_schema: string;
  reports: ReportInfo[];
}

export interface Tile { value: number | null; unit: string; status: Pill; scope: string; design_value?: number | null }
export type DomainKey = "completeness" | "accuracy" | "consistency" | "temporal" | "reliability";

export interface PerioDq {
  bench: string; bench_name: string; report: string; title: string; summary: string; gold_schema: string;
  source: "databricks" | "fixtures"; generated_ts: string; cached: boolean; synthetic: true;
  provenance: { loaded_ts: string | null; git_commit_sha: string | null; visit_count: number; clinic_count: number };
  clinics: string[];
  thresholds: Record<string, { direction: "higher" | "lower"; good: number; watch: number }>;
  tiles: Record<string, Record<DomainKey, Tile>>;
  missingness: { column: string; missing_pct: number; missing_count: number; row_count: number }[];
  checks: { clinic: string; category: string; check: string; checked_count: number; failed_count: number;
    pass_pct: number; status: string }[];
  scales: { method: string; method_label: string; scale: string; scale_label: string; visit_count: number;
    periodontitis_pct: number; stage3_4_pct: number }[];
  accuracy: { clinic: string; source: string; source_label: string; visit_count: number; answered_count: number;
    answered_pct: number | null; agree_pct: number | null }[];
  concordance: { methods: string[]; labels: string[]; agree_pct: (number | null)[][]; kappa: (number | null)[][] };
  prevalence: { overall_pct: number | null; clinics: { clinic: string; person_count: number; periodontitis_pct: number;
    ci_low_pct: number; ci_high_pct: number }[] };
  transitions: { stages: string[]; labels: string[]; row_pct: number[][]; count: number[][];
    direction: (string | null)[][] };
  temporal: { method: string; method_label: string; pair_count: number; improved_pct: number; same_pct: number;
    worse_pct: number; resolved_pct: number; stage_drop_pct: number }[];
  injected: { injected_count: number; caught_pct: number; false_flag_pct: number } | null;
}

async function getJson<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) {
    let detail = `${r.status} ${r.statusText}`;
    try { detail = (await r.json()).detail ?? detail; } catch { /* not JSON */ }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

export const fetchBenches = () => getJson<Bench[]>("/api/benches");
export const fetchReport = <T,>(bench: string, report: string) =>
  getJson<T>(`/api/benches/${encodeURIComponent(bench)}/reports/${encodeURIComponent(report)}`);
