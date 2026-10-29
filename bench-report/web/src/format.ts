export const fmt = (n: number | null | undefined, d = 1): string =>
  n == null ? "—" : n.toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: Number.isInteger(n) ? 0 : d });

// 0..1 -> a step of the sequential blue ramp (the design's --seq-100 .. --seq-700)
export const seq = (t: number): string => {
  const steps = ["--seq-100", "--seq-200", "--seq-300", "--seq-400", "--seq-500", "--seq-600", "--seq-700"];
  return `var(${steps[Math.min(6, Math.max(0, Math.round(t * 6)))]})`;
};

export const clinicName = (c: string) => (c === "All" ? "All clinics" : `Clinic ${c}`);

// evidence columns of dq_column_missing, in plain words; unknown ones show their code
const COLUMNS: Record<string, string> = {
  notes: "Chart note", exam_form: "Exam form", proc_dx_completed: "Diagnosis codes, done",
  proc_dx_planned: "Diagnosis codes, planned", probing_chart: "Gum measurements (any)",
  rec_max_cal_mm: "Max attachment loss (CAL)", rec_bop_pct: "Bleeding on probing",
  rec_max_probing_depth_mm: "Max probing depth", rec_teeth_lost_perio: "Teeth lost to gum disease",
  radiograph_ai: "Radiograph AI", algorithm_design: "Rules, exam form first (design)",
};
export const columnName = (c: string) => COLUMNS[c] ?? c;
