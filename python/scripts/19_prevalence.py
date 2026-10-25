"""Clinic-level periodontitis prevalence from the integrated phenotype (spec 005, US3).

    python scripts/19_prevalence.py

Person-level (latest visit with a known status), per clinic and overall, with
95% Wilson intervals, for: the study-design phenotype, the v0 phenotype, each
single source, and (synthetic only) the generator truth. Then the overall
estimate next to published US figures (NHANES 2009-2014) with the caveats in
prevalence.py. Writes data/datasets/prevalence/.
"""

import pandas as pd

from dental_omop_nlp.paths import DATASETS_DIR
from dental_omop_nlp.prevalence import NHANES_2009_2014, prevalence_by

v = pd.read_csv(DATASETS_DIR / "visits_structured.csv")
truth = pd.read_csv(DATASETS_DIR / "answer_key" / "visits_truth.csv")[["visit_id", "truth_status"]]
v = v.merge(truth, on="visit_id")
out = DATASETS_DIR / "prevalence"
out.mkdir(exist_ok=True)

methods = ["algorithm_design", "algorithm_v0", "notes", "exam_form", "proc_dx_completed", "probing_chart",
           "truth_status"]
by_clinic = pd.concat([prevalence_by(v, m, by="clinic_id").assign(method=m) for m in methods])
overall = pd.concat([prevalence_by(v, m).assign(method=m) for m in methods])
by_clinic.to_csv(out / "prevalence_by_clinic.csv", index=False)
overall.to_csv(out / "prevalence_overall.csv", index=False)

adults30 = v[v["age"] >= 30]
ov30 = pd.concat([prevalence_by(adults30, m).assign(method=m) for m in ("algorithm_design", "truth_status")])
nh = NHANES_2009_2014.iloc[0]
cmp = ov30.assign(published_total_pct=nh.total_pct, published_severe_pct=nh.severe_pct,
                  note="NHANES uses CDC/AAP definitions; 'severe' is not stage III-IV; clinic != national sample")
cmp.to_csv(out / "vs_published.csv", index=False)
NHANES_2009_2014.to_csv(out / "published_nhanes_2009_2014.csv", index=False)

pd.set_option("display.width", 160)
print("SYNTHETIC population: prevalence describes the generator, not any real clinic\n")
d = by_clinic[by_clinic.method.isin(["algorithm_design", "truth_status"])]
print(d.pivot(index="clinic_id", columns="method", values="periodontitis").round(3).to_string())
print("\nadults 30+, overall vs published (NHANES 2009-2014: 42.2% any, 7.8% severe):")
print(ov30[["method", "n_people", "periodontitis", "periodontitis_ci_low", "periodontitis_ci_high",
            "stage3_4"]].round(3).to_string(index=False))
