"""Architecture, ERD and process diagrams as draw.io files (same tooling as milliman-panel-notes).

Run:    python3 build_drawio.py          -> ../<name>.drawio
Render: see render.md (draw.io's own export engine, headless) -> ../<name>.png
Synthetic data only; personal learning project.
"""
from _helpers import DB, DBX, STORAGE, SECURITY, MGMT, box, dbx_icon, edge, entity, group, icon, lane, note, rel, reset, save, title

GREEN, GREEN_F = "#15803D", "#DCFCE7"
ORANGE, ORANGE_F = "#C2410C", "#FFEDD5"
BLUE, BLUE_F = "#1E3A5F", "#DBEAFE"
PURPLE, PURPLE_F = "#7C3AED", "#F3E8FF"
GREY, GREY_F = "#7D8998", "#F5F5F5"

# ====================================================================== d0: medallion architecture
reset()
title("Architecture: dental sources → bronze (PHI zone) → silver (de-identified) → gold (OMOP + dental) on Databricks")
for label, x, w in [("Source", 40, 230), ("Ingest", 290, 280), ("Bronze · Silver · Gold", 590, 560),
                    ("Query and process", 1170, 300), ("Serve", 1490, 170), ("Consumer", 1680, 150)]:
    lane(label, x, 70, w)
# sources
icon("s_ehr", "Dental EHR (future)\nchart notes · exam forms\nprobing chart", "traditional_server", "#232F3E", 120, 140, 48)
icon("s_pm", "Practice management / claims\nCDT procedure codes\nICD-10 diagnosis codes", "database", DB, 120, 300, 48)
icon("s_rad", "Radiograph AI (exploratory)\nbone level per tooth", "client", "#232F3E", 120, 460, 48)
box("s_syn", "Today: synthetic generator\n10_build_study (seeded)\nfake PHI on purpose", 50, 590, 210, 60, color=GREY, fill=GREY_F)
# ingest
dbx_icon("al", "Auto Loader\nfiles → volume (future)", "auto-loader", 330, 140, 48)
dbx_icon("lc", "Lakeflow Connect / JDBC\nEHR database (future)", "lakeflow-connect", 330, 300, 48)
box("in_api", "Job task: vendor API pull\n(future)", 310, 465, 220, 45, color=GREY, fill=GREY_F)
box("in_syn", "Job task: write synthetic\nsources to bronze", 310, 600, 220, 45, color=GREY, fill=GREY_F)
# lakehouse
group("g_lake", "Databricks lakehouse · one catalog per environment (dev · UAT · prod)", "dbxlake", 580, 110, 900, 600)
dbx_icon("dbxlogo", "", "databricks", 1430, 116, 32)
dbx_icon("uc", "Unity Catalog", "unity-catalog", 610, 150, 44)
box("gov", "Governance: bronze is the PHI zone (restricted grants); silver and gold de-identified only · lineage · tags · masks · audit",
    680, 150, 770, 44, color=SECURITY, fill="#FBE9EB")
dbx_icon("jobs", "Lakeflow Jobs", "lakeflow-jobs", 610, 225, 44)
box("cicd", "Asset Bundle: dev · UAT · prod targets · GitHub Actions CI/CD · jobs run as a service principal in UAT/prod",
    680, 225, 770, 44, color=GREY, fill=GREY_F)
box("bronze", "BRONZE · PHI zone\nraw notes (with PHI)\nforms · CDT · ICD-10\ncharts · radiograph JSON",
    600, 320, 165, 100, color="#A0522D", fill="#F6E7DA")
box("silver", "SILVER · de-identified\nnotes (passed leak gate)\none status per source\nsites: PD · CAL · BOP",
    810, 320, 165, 100, color="#6B7280", fill="#EEF0F2")
box("gold", "GOLD · OMOP + dental\nNOTE · NOTE_NLP\nMEASUREMENT (+ site)\nphenotype · results",
    1020, 320, 165, 100, color="#B8860B", fill="#FFF6D6")
note("bronze → silver: de-identify, leak gate · silver → gold: source readers, derived site measures, OMOP load, "
     "phenotype, reliability, prevalence", 600, 428, 420, 50)
dbx_icon("sdp", "Pipelines: de-id, readers,\nderived measures, DQ checks", "spark-declarative-pipelines", 640, 495, 48)
dbx_icon("dl", "Delta Lake\nbronze → silver → gold", "delta-lake", 860, 495, 48)
box("lb", "Lakebase (Postgres): OMOP + perio_chart (dev/test) · Label Studio DB · review queue · run ledger",
    600, 600, 575, 44, color=SECURITY, fill="#FBE9EB")
dbx_icon("wh", "SQL warehouse\nderived site measures\nai_query judge", "sql-warehouse", 1220, 320, 48)
dbx_icon("ms", "Model Serving\nLLM judge (MLflow make_judge)\nMedGemma", "model-serving", 1220, 450, 48)
dbx_icon("ml", "MLflow + UC models\nchallenger → champion\non the acceptance test", "notebooks", 1380, 450, 48)
dbx_icon("mon", "Data quality · plausibility\nalerts (future)", "lakeflow", 1380, 320, 48)
# serve
dbx_icon("bi", "AI/BI dashboards\nacceptance test · prevalence\nby clinic · data quality", "ai-bi-dashboards", 1550, 140, 48)
box("ls", "Label Studio\nde-identified tasks", 1505, 480, 150, 50, color=ORANGE, fill=ORANGE_F)
icon("atlas", "OHDSI tools\nAtlas · R (Postgres CDM)", "client", "#232F3E", 1556, 330, 48)
# consumers
icon("c1", "Study lead,\ndata science (R)", "users", "#232F3E", 1730, 140, 48)
icon("c2", "Periodontist\nreviewers", "users", "#232F3E", 1730, 481, 48)
icon("c3", "Researchers\n(cohorts)", "users", "#232F3E", 1730, 330, 48)
# edges
edge("s_ehr", "al", ""); edge("s_pm", "lc", ""); edge("s_rad", "in_api", "")
edge("s_syn", "in_syn", "")
edge("al", "bronze", "", exit=(1, 0.5), entry=(0, 0.2), via=[(570, 164), (570, 342)])
edge("lc", "bronze", "", exit=(1, 0.5), entry=(0, 0.45), via=[(560, 324), (560, 369)])
edge("in_api", "bronze", "", exit=(1, 0.5), entry=(0, 0.7), via=[(560, 487), (560, 397)])
edge("in_syn", "bronze", "", exit=(1, 0.5), entry=(0, 0.95), via=[(570, 622), (570, 424)])
edge("bronze", "silver", "")
edge("silver", "gold", "")
edge("gold", "wh", "")
edge("gold", "ms", "", exit=(1, 0.8), entry=(0, 0.5), via=[(1195, 408), (1195, 474)])
edge("ms", "ml", "")
edge("gold", "lb", "load", dashed=True, exit=(0.5, 1), entry=(0.85, 0))
edge("wh", "bi", "", exit=(1, 0.3), entry=(0, 0.5), via=[(1470, 334), (1470, 164)])
edge("lb", "ls", "tasks · labels", dashed=True, exit=(1, 0.5), entry=(0.5, 1), via=[(1580, 622)])
edge("lb", "atlas", "", exit=(1, 0.2), entry=(0, 0.5), via=[(1495, 609), (1495, 354)])
edge("bi", "c1", ""); edge("ls", "c2", "", exit=(1, 0.5), entry=(0, 0.5)); edge("atlas", "c3", "")
note("Today everything is synthetic: the generator writes fake-PHI notes to bronze so the de-identification and leak gate are exercised end to end. "
     "Only de-identified data leaves bronze (Label Studio, models, LLM endpoints). Same layout in every environment; code deployed, not data or models.",
     40, 730, 1790, 45)
save("d0_medallion_architecture", page_w=1860, page_h=790)

# ====================================================================== d1: study process
reset()
title("Study process: notes, exam forms, procedure codes and diagnoses, probing chart → phenotype and AI, validated against reviewers")
srcs = [("s1", "Chart notes"), ("s2", "Exam forms"), ("s3", "Procedure codes\ncompleted"), ("s4", "Procedure codes\nplanned"),
        ("s5", "Procedure diagnosis\ncodes, completed"), ("s6", "Procedure diagnosis\ncodes, planned"), ("s7", "Probing chart\nCAL · RBL · teeth lost")]
lane("Evidence types (one visit)", 40, 60, 1520)
for i, (cid, lab) in enumerate(srcs):
    box(cid, lab, 40 + i * 220, 110, 200, 60, color=BLUE, fill=BLUE_F)
box("rad", "Radiograph AI (exploratory) · bone level per tooth", 1210, 215, 350, 34, color=GREY, fill=GREY_F)
lane("Qualitative", 40, 270, 740)
box("cmp", "Compare each evidence type with every other\nagreement, kappa, coverage", 40, 320, 340, 60, color=GREEN, fill=GREEN_F)
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

# ====================================================================== d6: gold layer overview
GOLD, GOLD_F = "#B8860B", "#FFF6D6"
reset()
title("Gold layer: dental_omop.gold_dental_omop_perio — who writes each table, its grain and key, who reads it")
for label, x, w in [("Where results are made", 40, 300), ("Job that writes it (jobs.yml)", 360, 330),
                    ("dental_omop.gold_dental_omop_perio (9 tables)", 710, 800), ("Read by", 1530, 270)]:
    lane(label, x, 70, w)
# sources
box("s_kaggle", "Kaggle free GPU (MedGemma, GPU encoders)\nresults PR → data/datasets/", 50, 120, 280, 55, color=GREY, fill=GREY_F)
box("s_repo", "Laptop, committed to git\ndata/datasets/ai_predictions_*.csv\nllm_details_*.csv · results_manifest.csv", 50, 200, 280, 70, color=GREY, fill=GREY_F)
box("s_gpu", "Databricks serverless GPU\n(the reader job's own run)", 50, 300, 280, 50, color=GREY, fill=GREY_F)
box("s_key", "Answer key + committed predictions\nreview_key.csv (240 synthetic charts)\nsame inputs as the README leaderboard", 50, 420, 280, 70, color=GREY, fill=GREY_F)
box("s_deid", "De-identification benchmark\ndata/deid/scores.csv", 50, 520, 280, 50, color=GREY, fill=GREY_F)
box("s_ep", "Serving endpoint: LLM judge\npay-per-token · 'none' skips the judge", 50, 600, 280, 50, color=GREY, fill=GREY_F)
box("s_q", "judge_queue (stratified corpus sample)\nbuilt by hand, not by a job", 50, 680, 280, 50, color=GREY, fill=GREY_F)
# jobs
box("j10", "Load results · 10_load_results.py\nafter every deploy (deploy.yml)\nappends new file versions (SHA-256)\n+ one MLflow run per new LLM file", 370, 140, 310, 90, color=BLUE, fill=BLUE_F)
box("j03", "MedGemma reader · 03_medgemma_reader.py\nreplace_batch on (source, run_id, method)", 370, 295, 310, 60, color=BLUE, fill=BLUE_F)
box("j07", "Judge scorecard · 07_judge_scorecard.py\noverwrites all six tables each run;\njudgments kept and resumed", 370, 470, 310, 80, color=PURPLE, fill=PURPLE_F)
box("j02", "LLM judge · 02_llm_judge.sql (ai_query)\nCREATE OR REPLACE judgments", 370, 655, 310, 60, color=PURPLE, fill=PURPLE_F)
# gold
group("g_gold", "", "dbxlake", 710, 110, 800, 520)
dbx_icon("g_uc", "", "unity-catalog", 1470, 116, 30)
lane("Results from anywhere · spec 016", 730, 132, 260, 28)
lane("Judge scorecard and de-identification · spec 012", 1000, 132, 500, 28)
group("g_res", "", "plain", 730, 172, 260, 440)
group("g_judge", "", "plain", 1000, 172, 500, 440)
entity("e_rf", "result_files", ["PK sha256 (one file version)", "file · kind · method · rows", "source: repo · kaggle · run_url"], 740, 185, w=240, color=GOLD, fill=GOLD_F)
entity("e_ap", "ai_predictions", ["PK sha256 + visit_id  (run_id for databricks)", "method · visit_id · pred", "source: repo · kaggle · databricks"], 740, 305, w=240, color=GOLD, fill=GOLD_F)
entity("e_lr", "llm_reader_runs", ["PK sha256 + visit_id  (run_id for databricks)", "one LLM reader call per chart", "raw · quote · gate_ok · tokens · latency"], 740, 425, w=240, color=GOLD, fill=GOLD_F)
entity("e_ca", "chart_answers", ["PK visit_id + system", "system × chart (9,120 rows)", "answer · truth · difficulty"], 1010, 185, w=230, color=PURPLE, fill=PURPLE_F)
entity("e_jd", "judgments", ["PK visit_id + kind + answer", "one judge call (status or verdict)", "verdict · judge_status · quote · gate"], 1010, 305, w=230, color=PURPLE, fill=PURPLE_F)
entity("e_ds", "deid_scores", ["PK method + tier", "de-id engine × test tier (90 rows)", "recall · precision · leaks per 1k"], 1010, 470, w=230, color=GREY, fill=GREY_F)
entity("e_jm", "judge_metrics", ["PK system + metric", "system × metric (532 rows)", "vs_truth · vs_judge · corrected"], 1260, 185, w=230, color=PURPLE, fill=PURPLE_F)
entity("e_ja", "judge_agreement", ["PK group + value", "judge vs truth (10 rows)", "n · agreement · CI · kappa"], 1260, 305, w=230, color=PURPLE, fill=PURPLE_F)
entity("e_jr", "judge_run", ["PK kind (status · verdict · all)", "cost and speed (3 rows)", "usd · tokens · latency p50/p95"], 1260, 425, w=230, color=PURPLE, fill=PURPLE_F)
# read by
box("r_dash", "AI/BI dashboard 'Scorecard'\nPhenotyping + De-identification pages\n(databricks/dashboards/scorecard.lvdash.json)", 1545, 185, 245, 75, color=ORANGE, fill=ORANGE_F)
box("r_cost", "16_cost_effectiveness.py\n(corpus judgments, exported)", 1545, 330, 245, 50, color=ORANGE, fill=ORANGE_F)
box("r_sql", "SQL editor / notebooks\nany table, e.g. select source,\nmethod, count(*) from ai_predictions", 1545, 450, 245, 70, color=ORANGE, fill=ORANGE_F)
# edges: sources → jobs
edge("s_kaggle", "j10", "", exit=(1, 0.5), entry=(0, 0.2))
edge("s_repo", "j10", "", exit=(1, 0.5), entry=(0, 0.75))
edge("s_gpu", "j03", "")
edge("s_key", "j07", "", exit=(1, 0.5), entry=(0, 0.2))
edge("s_deid", "j07", "", exit=(1, 0.5), entry=(0, 0.6))
edge("s_ep", "j07", "", exit=(1, 0.3), entry=(0, 0.92), via=[(350, 615), (350, 544)])
edge("s_ep", "j02", "", dashed=True, exit=(1, 0.8), entry=(0, 0.25), via=[(345, 640), (345, 670)])
edge("s_q", "j02", "", exit=(1, 0.5), entry=(0, 0.75))
# jobs → gold
edge("j10", "e_rf", "", exit=(1, 0.2), entry=(0, 0.5), via=[(694, 158), (694, 233)])
edge("j10", "e_ap", "", exit=(1, 0.5), entry=(0, 0.35), via=[(702, 185), (702, 339)])
edge("j10", "e_lr", "", exit=(1, 0.8), entry=(0, 0.35), via=[(710, 212), (710, 459)])
edge("j03", "e_ap", "", exit=(1, 0.3), entry=(0, 0.8), via=[(718, 313), (718, 382)])
edge("j03", "e_lr", "", exit=(1, 0.7), entry=(0, 0.8), via=[(724, 337), (724, 502)])
edge("j07", "g_judge", "overwrite", exit=(1, 0.5), entry=(0.15, 1), via=[(696, 510), (696, 650), (1075, 650)])
edge("j02", "g_judge", "replaces judgments (other columns)", dashed=True, exit=(1, 0.5), entry=(0.35, 1), via=[(1175, 685)])
# gold → readers
edge("g_judge", "r_dash", "", exit=(1, 0.2), entry=(0, 0.5))
edge("e_jd", "r_cost", "", dashed=True, exit=(1, 0.8), entry=(0, 0.5), via=[(1250, 382), (1250, 413), (1520, 413), (1520, 355)])
box("warn", "Watch: judgments has two writers with different columns. 07 writes (visit_id, kind, answer, verdict, judge_status, …); "
            "02 writes (method, visit_id, pred, verdict, supported_status, …). Whichever ran last owns the table; the dashboard expects 07's.",
    710, 740, 1080, 45, color=DBX, fill="#FFF3F0")
note("Same names in every target (each environment is its own workspace). Synthetic data only. Also in the schema: the UC model perio_note_classifier "
     "(Models tab). The one function in the Catalog Explorer isn't created by this repo's code; the chart review agent's tools (planned) will be. "
     "Columns: d7 and d8; column-by-column reference: docs/gold_tables.md.", 40, 800, 1750, 45)
save("d6_gold_overview", page_w=1840, page_h=860)

# ====================================================================== d7: ERD, results tables
reset()
title("ERD (gold, spec 016): every model result in one place — result_files, ai_predictions, llm_reader_runs")
entity("rf", "result_files", ["PK sha256  STRING  (file version)", "file  STRING  e.g. ai_predictions_bert-base.csv", "kind  STRING  predictions · llm_details",
                              "method  STRING", "rows  BIGINT", "source  STRING  repo · kaggle", "run_url  STRING  (Kaggle workflow run)",
                              "git_commit  STRING", "loaded_at  TIMESTAMP"], 40, 90, w=330, color=GOLD, fill=GOLD_F)
entity("ap", "ai_predictions", ["PK sha256  STRING  (repo · kaggle rows)", "PK visit_id  BIGINT", "method  STRING", "pred  STRING  (one of six statuses)",
                                "source  STRING  repo · kaggle · databricks", "run_id  STRING  (databricks rows)", "run_ts  TIMESTAMP  (databricks rows)",
                                "git_commit  STRING", "loaded_at  TIMESTAMP  (Load results rows)"], 480, 90, w=350, color=GOLD, fill=GOLD_F)
entity("lr", "llm_reader_runs", ["PK sha256  STRING  (llm_details file)", "PK visit_id  BIGINT", "method  STRING", "model · backend  STRING",
                                 "prompt_version  STRING · shots  BIGINT", "input_tokens · output_tokens  BIGINT", "latency_s  DOUBLE",
                                 "raw  STRING  (model's full reply)", "status · grade · extent  STRING", "quote  STRING  (verbatim from the note)",
                                 "gate_ok  BOOLEAN  (quote gate passed)", "error  STRING", "fallback  BOOLEAN  (rules answered instead)",
                                 "pred  STRING  (final status)", "source  STRING", "run_id  STRING  (databricks rows)", "run_ts  TIMESTAMP",
                                 "git_commit  STRING", "loaded_at  TIMESTAMP  (Load results rows)", "truth · difficulty  STRING  (databricks rows)"],
       940, 90, w=380, color=GOLD, fill=GOLD_F)
entity("key", "review chart  (not a table: answer_key/review_key.csv)", ["PK visit_id  BIGINT  (240 synthetic charts)", "truth_status  STRING",
                                                                     "difficulty  STRING  L1 · L2 · L3", "note_text  STRING  (de-identified)"],
       40, 420, w=330, color=GREY, fill=GREY_F)
rel("ap", "rf", "sha256", exit=(0, 0.3), entry=(1, 0.3))
rel("lr", "rf", "sha256", exit=(0.5, 0), entry=(0.5, 0), via=[(1130, 70), (205, 70)])
rel("ap", "lr", "1 : 0..1", dashed=True, exit=(1, 0.5), entry=(0, 0.21), start="ERmandOne", end="ERzeroToOne")
rel("ap", "key", "visit_id", exit=(0.5, 1), entry=(1, 0.5), via=[(655, 479)])
rel("lr", "key", "visit_id", exit=(0, 0.85), entry=(1, 0.8), via=[(880, 467 + 30 * 0), (880, 514)])
note("Keys and idempotency. Load results rows (source repo · kaggle): one result_files row per file version; its rows in ai_predictions / llm_reader_runs "
     "carry that sha256, deleted then appended on a reload, so loading again adds nothing and a changed file is a new version (old rows stay). "
     "Reader job rows (source databricks): keyed by (source, run_id, method); a retry replaces them; their sha256 is the scratch CSV's and has no "
     "result_files row (dashed: a logical link, not enforced). ai_predictions ↔ llm_reader_runs: one LLM details row per LLM prediction, matched on method + visit_id + source (+ run_id for databricks rows). Delta has no enforced keys: PK marks the logical key. "
     "Probabilities (p_*) stay in the committed CSV. simulated_* files are never loaded.", 40, 590, 860, 105)
note("Read ai_predictions for one result per method: filter to the latest sha256 per (source, method), or to one run_id.", 40, 705, 860, 30)
save("d7_erd_gold_results", page_w=1360, page_h=760)

# ====================================================================== d8: ERD, judge scorecard tables
reset()
title("ERD (gold, spec 012): judge scorecard — chart_answers, judgments, judge_metrics, judge_agreement, judge_run, deid_scores")
entity("ca", "chart_answers", ["PK visit_id  BIGINT", "PK system  STRING", "answer  STRING  (null = no answer)", "difficulty  STRING  L1 · L2 · L3",
                               "truth  STRING  (generator's truth)"], 40, 90, w=320, color=PURPLE, fill=PURPLE_F)
entity("jd", "judgments", ["PK visit_id  BIGINT", "PK kind  STRING  status · verdict", "PK answer  STRING  (verdict rows)",
                           "verdict  STRING  correct · incorrect · not_determinable", "judge_status  STRING  (status rows)",
                           "quote  STRING  (verbatim from the note)", "gate_ok  BOOLEAN", "gate_reason  STRING", "endpoint  STRING",
                           "prompt_version  STRING", "prompt_tokens · completion_tokens  BIGINT", "latency_s  DOUBLE",
                           "simulated  BOOLEAN", "api_error  BOOLEAN  (asked again next run)"], 470, 90, w=370, color=PURPLE, fill=PURPLE_F)
entity("jr", "judge_run", ["PK kind  STRING  status · verdict · all", "calls · charts  BIGINT", "endpoint_errors · gate_failures  BIGINT",
                           "prompt_tokens · completion_tokens  DOUBLE", "usd · usd_per_chart  DOUBLE", "latency_mean_s · p50_s · p95_s  DOUBLE"],
       950, 90, w=340, color=PURPLE, fill=PURPLE_F)
entity("jm", "judge_metrics", ["PK system  STRING", "PK metric  STRING  correct · unsafe_rate · …", "group  STRING  (README group)",
                               "metric_label  STRING", "vs_truth  DOUBLE", "vs_truth_judged  DOUBLE", "vs_judge  DOUBLE",
                               "difference  DOUBLE  (vs_judge − vs_truth)", "n_judged  BIGINT", "corrected_accuracy  DOUBLE  (Rogan-Gladen)",
                               "ci_low · ci_high  DOUBLE", "judged_correct  DOUBLE", "verdict_sensitivity · _specificity  DOUBLE"],
       40, 330, w=320, color=PURPLE, fill=PURPLE_F)
entity("ja", "judge_agreement", ["PK group  STRING  all · truth_status · difficulty", "PK value  STRING", "label  STRING", "n  BIGINT",
                                 "coverage · agreement  DOUBLE", "ci_low · ci_high  DOUBLE", "kappa  DOUBLE"], 470, 470, w=370, color=PURPLE, fill=PURPLE_F)
entity("ds", "deid_scores  (standalone)", ["PK method  STRING  (de-id engine)", "PK tier  STRING  easy · hard · unseen · external · …",
                                           "group  STRING  (from method)", "n_notes · n_phi  BIGINT", "entity_recall · char_recall  DOUBLE",
                                           "char_precision  DOUBLE", "decoy_damage · hard_negative_damage  DOUBLE", "n_hard_negatives  BIGINT",
                                           "token_precision · token_recall · token_f1  DOUBLE", "leaked_per_1k_notes  DOUBLE", "avg_chars  DOUBLE"],
       950, 330, w=340, color=GREY, fill=GREY_F)
rel("ca", "jd", "verdict: visit_id + answer", exit=(1, 0.45), entry=(0, 0.2))
rel("ca", "jd", "status: visit_id", dashed=True, exit=(1, 0.85), entry=(0, 0.45), via=[(415, 205), (415, 226)])
rel("ca", "jm", "system", dashed=True, exit=(0.5, 1), entry=(0.5, 0))
rel("jd", "jm", "vs_judge · corrected", dashed=True, exit=(0, 0.8035), entry=(1, 0.1))
rel("jd", "ja", "status rows vs truth", dashed=True, exit=(0.5, 1), entry=(0.5, 0))
rel("jd", "jr", "kind", dashed=True, exit=(1, 0.3), entry=(0, 0.3))
note("Solid: row-level join (the dashboard's chart drill-down: chart_answers LEFT JOIN judgments s ON visit_id AND s.kind = 'status', "
     "LEFT JOIN judgments v ON visit_id AND v.kind = 'verdict' AND v.answer = a.answer). One verdict serves every system that gave that "
     "answer on that chart. Dashed: the summary table is computed from these rows in python/dental_omop_nlp/judge_scorecard.py, not joined.",
     40, 690, 1250, 50)
note("chart_answers.system equals ai_predictions.method for the AI systems, plus +rules4 variants, the rule-based phenotype and each evidence type alone. "
     "Metrics are computed in code, never by the LLM. Overwritten every run (judgments kept and resumed). CSV twins: data/datasets/judge/.",
     40, 745, 1250, 40)
save("d8_erd_gold_judge", page_w=1330, page_h=800)
