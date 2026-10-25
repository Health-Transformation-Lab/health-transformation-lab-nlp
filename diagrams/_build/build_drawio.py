"""Architecture, ERD and process diagrams as draw.io files (same tooling as milliman-panel-notes).

Run:    python3 build_drawio.py          -> ../<name>.drawio
Render: see render.md (draw.io's own export engine, headless) -> ../<name>.png
Synthetic data only; personal learning project.
"""
from _helpers import DBX, STORAGE, SECURITY, MGMT, box, dbx_icon, edge, entity, group, lane, note, rel, reset, save, title

GREEN, GREEN_F = "#15803D", "#DCFCE7"
ORANGE, ORANGE_F = "#C2410C", "#FFEDD5"
BLUE, BLUE_F = "#1E3A5F", "#DBEAFE"
PURPLE, PURPLE_F = "#7C3AED", "#F3E8FF"
GREY, GREY_F = "#7D8998", "#F5F5F5"

# ====================================================================== d1: study process
reset()
title("Study process: notes, exam forms, procedure codes and diagnoses, probing chart → phenotype and AI, validated against reviewers")
srcs = [("s1", "Chart notes"), ("s2", "Exam forms"), ("s3", "Procedure codes\ncompleted"), ("s4", "Procedure codes\nplanned"),
        ("s5", "Procedure diagnoses\ncompleted"), ("s6", "Procedure diagnoses\nplanned"), ("s7", "Probing chart\nCAL · RBL · teeth lost")]
lane("Sources (one visit)", 40, 60, 1520)
for i, (cid, lab) in enumerate(srcs):
    box(cid, lab, 40 + i * 220, 110, 200, 60, color=BLUE, fill=BLUE_F)
box("rad", "Radiograph AI (exploratory) · bone level per tooth", 1210, 215, 350, 34, color=GREY, fill=GREY_F)
lane("Qualitative", 40, 270, 740)
box("cmp", "Compare each source with every other\nagreement, kappa, coverage", 40, 320, 340, 60, color=GREEN, fill=GREEN_F)
box("qr", "Qualitative review\ntwo dental reviewers, disagreeing charts", 420, 320, 360, 60, color=GREEN, fill=GREEN_F)
lane("Quantitative", 820, 270, 740)
box("alg", "Rule-based phenotype\nstudy-design order: exam form > dx code > notes > chart\n(all 24 orders scored)", 820, 320, 360, 70, color=ORANGE, fill=ORANGE_F)
box("rev", "Many reviewers stage the same charts\nLabel Studio, independently", 1210, 320, 350, 70, color=ORANGE, fill=ORANGE_F)
box("ai", "AI models read the note only\nrules · TF-IDF · 12 BERT models · MedGemma", 40, 470, 520, 60, color=PURPLE, fill=PURPLE_F)
box("acc", "Acceptance test: agree with reviewers at least as much as they agree with each other\nmean kappa vs each reviewer − mean reviewer-pair kappa, bootstrap CI, margin set in advance\nsix and five categories · unsafe errors · by difficulty", 640, 460, 920, 80, color=DBX, fill="#FFF3F0")
box("val", "Over time and at scale\nplausibility · data quality · clinic prevalence · progression\nLLM judge + cost at 1M notes", 640, 590, 920, 65, color=GREY, fill=GREY_F)
for i, (cid, _) in enumerate(srcs):
    edge(cid, "cmp", "", exit=(0.5, 1), entry=(0.5, 0), via=[(140 + i * 220, 196), (210, 196)])
edge("cmp", "qr", "")
edge("qr", "alg", "rules")
edge("alg", "acc", "")
edge("rev", "acc", "")
edge("s1", "ai", "notes only", dashed=True, exit=(0, 0.5), entry=(0, 0.5), via=[(25, 140), (25, 500)])
edge("ai", "acc", "")
edge("acc", "val", "")
edge("rad", "alg", "lower bound (v0 only)", dashed=True, exit=(0, 0.5), entry=(0.5, 0), via=[(1000, 232)])
note("Synthetic patients and simulated reviewers until real data is approved. Code walkthrough: docs/code_walkthrough.md.", 40, 680, 1500, 30)
save("d1_study_process", page_w=1600, page_h=730)

# ====================================================================== d2: platform architecture
reset()
title("Platform: one bundle, three environments (dev · UAT · prod) on Databricks")
group("g_gh", "GitHub · jcbowyer/dental-omop-nlp", "ext", 40, 70, 380, 330)
group("g_ls", "Label Studio (separate app)", "ext", 40, 430, 380, 230)
box("code", "Python + R code, SQL, notebooks\nspecs/, tests, parity", 70, 120, 320, 55, color=GREY, fill=GREY_F)
box("ci", "ci.yml: pytest · R parity · Postgres tests\n· bundle validate", 70, 200, 320, 55, color=GREY, fill=GREY_F)
box("cd", "deploy.yml: uat on push to main\nprod on demand, approval required\nas a service principal", 70, 280, 320, 70, color=GREY, fill=GREY_F)
group("g_dbx", "Databricks workspace (per target: catalog.schema, Lakebase instance, experiment, model)", "dbx", 470, 70, 1090, 620)
dbx_icon("i_jobs", "Lakeflow Jobs", "lakeflow-jobs", 500, 120)
box("jobs", "study_benchmark · load_lakebase · llm_judge\nmedgemma_reader (GPU, uat/prod)\nnotebooks 00–04", 580, 115, 330, 70)
dbx_icon("i_uc", "Unity Catalog", "unity-catalog", 500, 230)
box("delta", "Delta tables · catalog.schema per target\nOMOP CDM + dental extension, sources,\npredictions, reliability, judge, cost", 580, 225, 330, 75, color=STORAGE, fill="#F2F6E8")
dbx_icon("i_lb", "Lakebase", "databricks", 500, 340)
box("lake", "Lakebase (Postgres)\nOMOP CDM + perio_chart view (dev/test)\nreview queue · live labels · run ledger", 580, 335, 330, 75, color=SECURITY, fill="#FBE9EB")
dbx_icon("i_ml", "MLflow", "notebooks", 960, 120)
box("mlf", "MLflow experiment per target\nruns tagged step · git commit · dataset · simulated", 1040, 115, 490, 60, color=MGMT, fill="#FDE7F1")
box("reg", "UC model catalog.schema.perio_note_classifier\nchallenger → champion only if acceptance test non-inferior\nand at least as good as current champion", 1040, 195, 490, 75, color=MGMT, fill="#FDE7F1")
dbx_icon("i_ms", "Model Serving", "model-serving", 960, 300)
box("srv", "Serving endpoints: LLM judge (MLflow make_judge / ai_query),\nMedGemma (paid workspaces); Free Edition: notebook GPU", 1040, 295, 490, 60)
dbx_icon("i_sql", "SQL warehouse", "sql-warehouse", 960, 390)
box("sql", "ai_query judge at corpus scale · derived site measures", 1040, 390, 490, 45)
box("ls", "One project per reviewer\nde-identified tasks only\nits database can be Lakebase", 70, 475, 320, 70, color=ORANGE, fill=ORANGE_F)
box("rev", "Reviewers stage charts independently", 70, 585, 320, 45, color=ORANGE, fill=ORANGE_F)
box("dq", "Data quality · plausibility · prevalence per clinic\n(future: inference tables + data profiling, alerts)", 1040, 470, 490, 60, color=GREY, fill=GREY_F)
note("dev = your sandbox (Free Edition, resources prefixed [dev yourname]); uat = shared test; prod = approved release. Synthetic data in every target until approval.", 470, 640, 1090, 40)
edge("code", "ci", "")
edge("ci", "cd", "")
edge("cd", "jobs", "bundle deploy", exit=(1, 0.5), entry=(0, 0.5), via=[(440, 315), (440, 150)])
edge("jobs", "delta", "")
edge("jobs", "lake", "", dashed=True, exit=(0, 0.85), entry=(0, 0.5), via=[(568, 175), (568, 372)])
edge("jobs", "mlf", "")
edge("mlf", "reg", "register")
edge("reg", "srv", "@champion", dashed=True)
edge("srv", "sql", "", dashed=True)
edge("lake", "ls", "tasks out · labels in", exit=(0.3, 1), entry=(1, 0.5), via=[(679, 510)])
edge("rev", "ls", "labels")
save("d2_platform_architecture", page_w=1600, page_h=700)

# ====================================================================== d3: ERD
reset()
title("ERD: OMOP CDM 5.4 tables used here + dental extension (SITE, SITE_EVENT) + local concepts")
# column 1: person, visit, note, note_nlp
entity("person", "PERSON", ["PK person_id", "gender_concept_id", "year_of_birth", "race_concept_id", "ethnicity_concept_id"], 40, 80, w=250)
entity("visit", "VISIT_OCCURRENCE", ["PK visit_occurrence_id", "FK person_id", "visit_concept_id (9202 outpatient)",
                                     "visit_start_date / end_date", "visit_type_concept_id"], 40, 300, w=250)
entity("note", "NOTE", ["PK note_id", "FK person_id", "FK visit_occurrence_id", "note_text (de-identified)",
                        "note_type / class / encoding / language"], 40, 520, w=250)
entity("nlp", "NOTE_NLP", ["PK note_nlp_id", "FK note_id", "lexical_variant, term", "note_nlp_concept_id (status)",
                           "nlp_system (model + version)", "flag for review, never a diagnosis"], 40, 740, w=250, color=PURPLE, fill=PURPLE_F)
# column 2: measurement
entity("meas", "MEASUREMENT", ["PK measurement_id", "FK person_id", "FK visit_occurrence_id", "FK measurement_concept_id",
                                "value_as_number", "measurement_date", "measurement_source_value",
                                "tooth_number  (design C only)", "tooth_site  (design C only)"], 420, 110, w=270)
# column 3: dental extension
entity("sev", "SITE_EVENT  (dental extension)", ["PK site_event_id", "FK site_id", "event_id → measurement_id",
                                                 "event_field_concept_id (1147138)", "site_event_type_concept_id"],
       800, 110, w=280, color=DBX, fill="#FFF3F0")
entity("site", "SITE  (dental extension)", ["PK site_id", "FK person_id", "site_concept_id (tooth / tooth-site)",
                                            "site_source_value '3' / '3-MB'", "FK parent_site_id (the tooth)",
                                            "site_start_date / end_date"], 800, 340, w=280, color=DBX, fill="#FFF3F0")
# column 4: vocabulary and view
entity("concept", "CONCEPT", ["PK concept_id", "concept_code", "vocabulary_id", "domain_id", "standard_concept"], 1190, 110, w=320)
entity("loc", "Local concepts  (DENTAL_LOCAL rows in CONCEPT)", ["SITE_PD · SITE_CAL · SITE_BOP", "TOOTH_STATUS · FURCATION · MOBILITY",
                                                "PERIO_MAX_CAL · PERIO_BOP_PCT ... (derived)", "N_TEETH_IP_CAL3/4/6 · N_TEETH_IP_PD4/5",
                                                "N_SITES_IP_PD5 · CDC_AAP_* · PERIO_STATUS_*"], 1190, 310, w=320, color=GREEN, fill=GREEN_F)
entity("view", "perio_chart  (view over MEASUREMENT)", ["person_id, visit_occurrence_id, exam_date", "max_probing_depth_mm, bop_pct",
                                       "max_cal_mm, rbl_pct, teeth_lost_perio"], 1190, 520, w=320, color=GREY, fill=GREY_F)
rel("visit", "person", exit=(0.5, 0), entry=(0.5, 1))
rel("note", "visit", exit=(0.5, 0), entry=(0.5, 1))
rel("nlp", "note", exit=(0.5, 0), entry=(0.5, 1))
rel("meas", "person", "person_id", exit=(0, 0.12), entry=(1, 0.4))
rel("meas", "visit", "visit_occurrence_id", exit=(0, 0.3), entry=(1, 0.3), via=[(350, 186), (350, 352)])
rel("sev", "meas", "event_id", exit=(0, 0.35), entry=(1, 0.15))
rel("sev", "site", "site_id", exit=(0.5, 1), entry=(0.5, 0))
rel("site", "site", "parent_site_id", exit=(1, 0.75), entry=(1, 0.55), via=[(1120, 468), (1120, 435)])
rel("site", "person", "person_id", exit=(0.5, 1), entry=(1, 0.75), via=[(940, 520), (330, 520), (330, 196)])
rel("meas", "concept", "measurement_concept_id", exit=(0.5, 0), entry=(0.5, 0), via=[(555, 72), (1350, 72)])
rel("loc", "concept", "", dashed=True, exit=(0.5, 0), entry=(0.5, 1))
rel("view", "meas", "pivots", dashed=True, exit=(0, 0.5), entry=(0.5, 1), via=[(555, 581)])
note("Design A links each site measurement through SITE_EVENT; design B encodes tooth and site in the concept (PD|3|MB); "
     "design C adds tooth_number / tooth_site to MEASUREMENT. See d4 and docs/site_level_omop.md.", 40, 920, 1470, 40)
save("d3_erd_omop_dental", page_w=1560, page_h=970)

# ====================================================================== d4: site storage designs
reset()
title("Three ways to store site-level periodontal data in OMOP (same mouths, same results)")
for i, (name, color, fill, rows, stats) in enumerate([
        ("A. Post-coordinated (SITE / SITE_EVENT)", DBX, "#FFF3F0",
         ["MEASUREMENT: concept SITE_PD, value 5", "SITE_EVENT: measurement_id → site_id", "SITE 3-MB → parent SITE 3",
          "query: 5 joins, 1 decode"], "529 MB · 6.8 s · base OMOP unchanged · link table as big as MEASUREMENT"),
        ("B. Pre-coordinated concepts", ORANGE, ORANGE_F,
         ["MEASUREMENT: concept 'PD|3|MB', value 5", "CONCEPT: 672 local concepts", "tooth, site decoded from concept_code",
          "query: 2 joins, 11 decodes"], "276 MB · 4.2 s · base OMOP unchanged · concepts don't exist as standard"),
        ("C. Site columns", GREEN, GREEN_F,
         ["MEASUREMENT: concept SITE_PD, value 5", "+ tooth_number 3, tooth_site 'MB'", "nothing to decode",
          "query: 0 joins"], "309 MB · 2.2 s · simplest, fastest · changes a CDM table")]):
    x = 40 + i * 510
    group(f"g{i}", name, "plain", x, 70, 480, 340)
    for j, r in enumerate(rows):
        box(f"r{i}{j}", r, x + 20, 115 + j * 62, 440, 48, color=color, fill=fill)
    note(stats, x + 20, 365, 440, 40)
box("tail", "Shared derived-measure SQL (derived_tail.sql): max PD, max interproximal CAL, % bleeding, teeth lost,\n"
            "counts of different teeth with CAL ≥ 3/4/6 and PD ≥ 4/5 → 2017 AAP/EFP stage and 2012 CDC/AAP category", 40, 450, 1500, 60, color=BLUE, fill=BLUE_F)
for i in range(3):
    edge(f"g{i}", "tail", "", exit=(0.5, 1), entry=(0.16 + 0.34 * i, 0))
box("wb", "Write derived measures back as MEASUREMENT rows (local concepts) → Atlas cohorts can threshold them", 40, 550, 1500, 45, color=GREY, fill=GREY_F)
edge("tail", "wb", "")
note("Postgres 16 (Lakebase-compatible), 3,437 synthetic exams, 2.16M measurement rows, all three equal Python exactly. scripts/23_site_designs.py", 40, 620, 1500, 30)
save("d4_site_storage_designs", page_w=1600, page_h=670)

# ====================================================================== d5: MLOps lifecycle
reset()
title("MLOps: deploy code, train per environment, promote on the acceptance test")
steps = [("t1", "Train / fit rung\n11_ai_predict.py", BLUE, BLUE_F), ("t2", "Log run + pyfunc\nMLflow (tags: commit,\ndataset, simulated)", MGMT, "#FDE7F1"),
         ("t3", "Register version\nUC model · alias\nchallenger", MGMT, "#FDE7F1"), ("t4", "Acceptance test\n13_reliability.py\nvs reviewers", DBX, "#FFF3F0"),
         ("t5", "Promote?\n24_promote_model.py\nnon-inferior and ≥ champion", ORANGE, ORANGE_F), ("t6", "Alias champion\nbatch scoring /\nserving loads @champion", GREEN, GREEN_F)]
for i, (cid, lab, c, f) in enumerate(steps):
    box(cid, lab, 40 + i * 255, 110, 225, 80, color=c, fill=f)
    if i:
        edge(steps[i - 1][0], cid, "")
box("stay", "stays challenger\nverdict + diff tagged on the version", 1060, 250, 225, 60, color=GREY, fill=GREY_F)
edge("t5", "stay", "no", exit=(0.5, 1), entry=(0.5, 0))
box("judge", "LLM judge (MLflow make_judge, same AAP criteria, quote gate)\nmlflow.genai.evaluate: one trace per chart · aligned to reviewer labels", 40, 260, 700, 60, color=PURPLE, fill=PURPLE_F)
box("mon", "Monitor: data quality, plausibility over time, prevalence per clinic\nnext: inference tables, data profiling, alerts → retrain", 40, 360, 700, 60, color=GREY, fill=GREY_F)
edge("t6", "mon", "", exit=(0.5, 1), entry=(1, 0.5), via=[(1462, 390)])
edge("mon", "t1", "", dashed=True, exit=(0, 0.5), entry=(0, 0.5), via=[(20, 390), (20, 150)])
edge("judge", "t4", "accuracy at corpus scale", dashed=True, exit=(1, 0.5), entry=(0.5, 1), via=[(892, 290)])
note("Dashed loop on the left: retraining (future). dev · uat · prod each have their own experiment, UC model and data (databricks/resources/mlops.yml). docs/mlops.md", 40, 450, 1500, 30)
save("d5_mlops_lifecycle", page_w=1600, page_h=500)
