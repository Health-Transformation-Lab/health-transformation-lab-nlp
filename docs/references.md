# References

Everything this repo relies on, and what it's used for.

## Dental NLP and phenotyping

1. **Chuang Y-S, et al.**
   *Extracting periodontitis diagnosis in clinical notes with RoBERTa and regular expression.*
   [arXiv 2311.10809](https://arxiv.org/abs/2311.10809). UTHealth Houston, 8,125 notes.
   → Published diagnosis-line forms and the 98.7% diagnosis-section rate
   ([note_realism.md](note_realism.md)); regex baseline design.
2. **Chuang Y-S, Lee C-T, Tokede O, Lin G-H, Brandon R, Tran TD, Jiang X, Walji MF.**
   *Artificial Intelligence in Extracting Diagnostic Data from Dental Records.*
   [arXiv 2407.21050](https://arxiv.org/abs/2407.21050v3). UTHealth + UCSF.
   → Label schema (status, stage, grade, extent); 240 dentist-labeled notes per
   site as the test-set size; synthetic-train / real-test design; the extent trap.
3. **Patel JS.** *Utilizing Electronic Dental Record Data to Track Periodontal
   Disease Change.* PhD dissertation, IUPUI, 2020.
   [IU ScholarWorks](https://scholarworks.indianapolis.iu.edu/items/0768bd4f-e24a-465a-95fe-b8cabca06c68/full).
   → 47% agreement between charting-derived and clinician-recorded diagnoses;
   charting present for ~80% of patients (both modeled in the generator).
4. **Patel JS, Brandon R, Tellez M, Albandar JM, Rao R, Krois J, Wu H.**
   *Developing Automated Computer Algorithms to Phenotype Periodontal Disease
   Diagnoses in Electronic Dental Records.* Methods of Information in Medicine, 2022.
   → Prior work on rule-based phenotyping from EDR data (study design context).
5. **Patel JS, Rao R, Tellez M, Albandar M, Joachim K, Wu H.** *Natural Language
   Processing Applications to Extract Periodontal Disease and Medical History
   Information from Electronic Dental Records.* ICMHI, 2022.

## Evaluation methods

6. **Cai Z, Zhao J, et al.** *GlobalDentBench: A Multinational Benchmark for
   Evaluating LLM Clinical Reasoning in Dentistry with Expert Calibration.*
   [arXiv 2605.24636](https://arxiv.org/abs/2605.24636), May 2026.
   Code: github.com/FreedomIntelligence/GlobalDentBench.
   → Safety severity S0/S1/S2, reasoning levels, judge selection, key-point
   scoring ([dentbench_methods.md](dentbench_methods.md)).

## Data models and classification

7. **Tonetti MS, Greenwell H, Kornman KS.** *Staging and grading of periodontitis:
   Framework and proposal of a new classification and case definition.*
   J Periodontol 2018;89(Suppl 1):S159–S172. → Stage, grade, extent rules (`labels.py`).
8. **Armitage GC.** *Development of a classification system for periodontal
   diseases and conditions.* Ann Periodontol 1999;4(1):1–6. → Pre-2017 terms
   (slight / moderate / severe chronic periodontitis).
9. **OHDSI Dentistry Workgroup (Koski R et al.).** *Mapping Dental Use Cases to the
   OMOP-CDM: Vocabulary and Common Data Model Evaluation.* OHDSI Symposium 2023.
   [PDF](https://ohdsi.org/wp-content/uploads/2023/10/39-Koski-OHDSIreport-Robert-Koski.pdf).
   → `SITE` / `SITE_EVENT` tooth-level extension.
10. **OHDSI.** OMOP Common Data Model v5.4. [ohdsi.github.io/CommonDataModel](https://ohdsi.github.io/CommonDataModel/).

## Radiographs (exploratory)

19. **Overjet.** *How to detect periodontal disease with AI* (bone level measurement, FDA 510(k) K210187).
    [overjet.com](https://www.overjet.com/blog/how-to-detect-periodontal-disease-with-ai)
20. **MATTER / CareQuest Innovation Partners.** *2026 SMILE Health cohort and newest ACCELERATE pilots*, June 2026.
    [matter.health](https://matter.health/posts/carequest-innovation-partners-2026-smile-health-cohort-accelerate-pilots/)
21. **Yavuz MB, et al.** AI detection of periodontal status in bitewing radiographs. EuroPerio10, 2022.
    [Dental Tribune summary](https://www.dental-tribune.com/news/artificial-intelligence-shows-promise-for-detecting-periodontal-status-in-bitewing-radiographs/)

## Case validation (the acceptance test)

27. **OHDSI.** *OHDSI2023 Plenary: Improving the reliability and scale of case validation*
    (Ryan, Ostropolets, Schuemie). [YouTube](https://www.youtube.com/watch?v=scUssf863TI), from about 49 min.
28. **Schuemie MJ, Ostropolets A, Zhuk A, Korsik U, Seo SI, Suchard MA, Hripcsak G, Ryan PB.**
    *Standardized patient profile review using large language models for case adjudication in
    observational research.* npj Digital Medicine 2025;8.
    [doi:10.1038/s41746-025-01433-4](https://doi.org/10.1038/s41746-025-01433-4)

## Knowledge graphs, retrieval and OMOP vocabulary

29. **Lee J, Liu C, Kim JH, et al. (Columbia).** *Comparative effectiveness of knowledge graphs- and EHR
    data-based medical concept embedding for phenotyping.* medRxiv 2020.
    [link](https://www.medrxiv.org/content/10.1101/2020.07.14.20151274v1.abstract)
30. **Ahmed A, Soby S, Aasman B, Mirhaji P.** *Automated OMOP concept mapping using multi-agent LLMs and
    graph-enhanced semantic retrieval.* OHDSI Symposium 2025.
    [PDF](https://www.ohdsi.org/wp-content/uploads/2025/10/508-Ahmed-Automated-OMOP-Concept-Mapping-Using-Multi-Agent-Large-Language-Models-and-Graph-Enhanced-Semantic-Retrieval-Report-Adil-Ahmed.pdf)
31. **Thio S, Lewis M, Denaxas S, Dobson RJB.** *Unlocking electronic health records: a hybrid graph RAG
    approach to safe clinical AI for patient QA.* arXiv 2602.00009. [link](https://www.arxiv.org/abs/2602.00009)
32. **Zhao X, Liu S, Yang S-Y, Miao C.** *MedRAG.* arXiv 2502.04413. [link](https://arxiv.org/abs/2502.04413v2)

## Platform

33. **Databricks.** *Lakebase release notes.* [docs](https://docs.databricks.com/aws/en/release-notes/lakebase/)
34. **Databricks.** *Free Edition limitations.* [docs](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)

## Epidemiology and data quality

35. **Eke PI, Thornton-Evans GO, Wei L, Borgnakke WS, Dye BA, Genco RJ.** *Periodontitis in US adults:
    National Health and Nutrition Examination Survey 2009-2014.* J Am Dent Assoc 2018;149(7):576-588.
    [doi:10.1016/j.adaj.2018.04.023](https://doi.org/10.1016/j.adaj.2018.04.023); figures via
    [NIDCR](https://nidcr.nih.gov/research/data-statistics/periodontal-disease/adults)
36. **Kahn MG, Callahan TJ, Barnard J, et al.** *A harmonized data quality assessment terminology and framework
    for the secondary use of electronic health record data.* eGEMs 2016;4(1):1244.
    [doi:10.13063/2327-9214.1244](https://doi.org/10.13063/2327-9214.1244)

## Classification rules

26. **American Academy of Periodontology.** *Staging and Grading Periodontitis* (worksheet).
    [perio.org PDF](https://www.perio.org/wp-content/uploads/2019/08/Staging-and-Grading-Periodontitis.pdf).
    The rule source for this repo; see [staging_grading.md](staging_grading.md).

## Medical LLMs (exploratory)

22. **Sellergren A, et al.** *MedGemma Technical Report.* [arXiv 2507.05201](https://arxiv.org/abs/2507.05201), 2025.
23. **Google Health AI Developer Foundations.** *MedGemma model card.*
    [developers.google.com](https://developers.google.com/health-ai-developer-foundations/medgemma/model-card-v1)
24. **BioPharmaTrend.** *Google updates open medical AI suite with new imaging and speech models* (MedGemma 1.5, MedASR), January 2026.
    [biopharmatrend.com](https://www.biopharmatrend.com/news/google-updates-open-medical-ai-suite-with-new-imaging-and-speech-models-launches-100k-developer-hackathon-1464/)

25. **Koski R, et al.** *Identifying Oral Health Concepts in OMOP-CDM Datasets.* OHDSI Symposium 2025.
    [PDF](https://www.ohdsi.org/wp-content/uploads/2025/10/111-koski-robert_Identifying_Oral_Health_Concepts-Robert-Koski.pdf)

## Synthetic data

11. **Tamizh Selvam T.** *Synthetic Dental Clinical Notes Dataset for Dental NLP
    Benchmarking.* IEEE DataPort, 2026. DOI 10.21227/tt32-vp70.
    → Candidate external test set ([data_sources.md](data_sources.md)).
12. **Walonoski J, et al.** *Synthea: An approach, method, and software mechanism
    for generating synthetic patients and the synthetic electronic health care
    record.* JAMIA 2018;25(3):230–238.

## Statistics

13. **Rogan WJ, Gladen B.** *Estimating prevalence from the results of a screening
    test.* Am J Epidemiol 1978;107(1):71–76. → Correcting judge-estimated accuracy.
14. **Fleiss JL.** *Measuring nominal scale agreement among many raters.*
    Psychol Bull 1971;76(5):378–382. → Reviewer reliability.
15. **Cohen J.** *Weighted kappa.* Psychol Bull 1968;70(4):213–220. → Ordinal agreement.
51. **Patel JS, et al.** *Developing and testing a prediction model for periodontal disease using machine
    learning and big electronic dental record data.* Frontiers in Artificial Intelligence 2022.
    doi:10.3389/frai.2022.979525. → Design of the status classifier (`classify_status.py`, spec 013 G10):
    XGBoost, 80/20 split, 5-fold cross-validated hyperparameters, one-vs-all metrics. Whether it used SHAP
    was not checked against the full text; SHAP here is this repo's choice.
52. **Lundberg SM, Erion G, Chen H, et al.** *From local explanations to global understanding with
    explainable AI for trees.* Nature Machine Intelligence 2020;2:56–67. → TreeSHAP, the exact SHAP values
    XGBoost computes (`pred_contribs`) for the status classifier.

## De-identification

37. **U.S. Department of Health and Human Services.** *Guidance regarding methods for de-identification of
    protected health information in accordance with the HIPAA Privacy Rule* (Safe Harbor's 18 identifiers;
    Expert Determination). [hhs.gov](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html)
    → The PHI categories in the challenge set.
38. **Stubbs A, Uzuner Ö.** *Annotating longitudinal clinical narratives for de-identification: the 2014
    i2b2/UTHealth corpus.* J Biomed Inform 2015;58(Suppl):S20–S29. Challenge page:
    [n2c2](https://n2c2.dbmi.hms.harvard.edu/challenge/2014-deidentification-heart-disease)
    → Annotation categories (patient, doctor, relative, profession, organization ...). The corpus itself
    needs a data use agreement and isn't used here.
39. **Microsoft.** *De-identification service in Azure Health Data Services* (TAG, REDACT, SURROGATE; 27 PHI
    categories). [learn.microsoft.com](https://learn.microsoft.com/en-us/azure/healthcare-apis/deidentification/overview);
    pricing: [azure.microsoft.com](https://azure.microsoft.com/pricing/details/health-data-services/)
40. **Microsoft.** *Azure AI Language: PII detection* (healthcare / PHI domain). Pricing:
    [azure.microsoft.com](https://azure.microsoft.com/pricing/details/cognitive-services/text-analytics/)
41. **Microsoft Presidio** — open-source PII detection (spaCy NER and pattern recognizers).
    [github.com/microsoft/presidio](https://github.com/microsoft/presidio)

42. **Weatherhead J.** *ASQ-PHI: an adversarial synthetic benchmark for clinical de-identification and search
    utility.* Mendeley Data, 2025, [doi:10.17632/csz5dzp7nx.1](https://data.mendeley.com/datasets/csz5dzp7nx/1)
    (MIT). 1,051 fully synthetic clinical search queries, 2,973 tagged PHI elements, 219 hard negatives.
43. **Posada JD, Datta S, Love D, Desai P.** *SHIELD: a diverse clinical note dataset and distilled small
    language models for enterprise-scale de-identification.* [arXiv:2605.03301](https://arxiv.org/abs/2605.03301);
    access: [github.com/susom/shield_dataset](https://github.com/susom/shield_dataset). Real notes with surrogate
    PHI, 10,229 adjudicated spans.
44. **presidio-evaluator** (presidio-research, MIT) — fake-PII sentence generator from templates, and
    evaluation of PII detectors. [pypi.org/project/presidio-evaluator](https://pypi.org/project/presidio-evaluator/)
45. **John Snow Labs.** *Clinical de-identification at scale: pipeline design and speed–accuracy trade-offs
    across infrastructures* (benchmarks on Databricks).
    [johnsnowlabs.com](https://www.johnsnowlabs.com/clinical-de-identification-at-scale-pipeline-design-and-speed-accuracy-trade-offs-across-infrastructures/)

46. **Chambon PJ, Wu C, Steinkamp JM, Adleberg J, Cook TS, Langlotz CP.** *Automated deidentification of
    radiology reports combining transformer and "hide in plain sight" rule-based methods.* J Am Med Inform
    Assoc, [doi:10.1093/jamia/ocac219](https://doi.org/10.1093/jamia/ocac219). Model:
    [StanfordAIMI/stanford-deidentifier-base](https://huggingface.co/StanfordAIMI/stanford-deidentifier-base) (MIT).
47. **Robust DeID** (OBI) — package [robust-deid](https://pypi.org/project/robust-deid/); model [obi/deid_roberta_i2b2](https://huggingface.co/obi/deid_roberta_i2b2)
    (RoBERTa trained on i2b2 2014; MIT).
48. **Kocaman V, Santas M, Gul Y, Butgul M, Talby D.** *Can zero-shot commercial APIs deliver regulatory-grade
    clinical text de-identification?* [arXiv:2503.20794](https://arxiv.org/abs/2503.20794), 2025. Authors are
    from John Snow Labs, one of the compared vendors.

49. **PhysioNet.** *Deidentified Medical Text* (Neamatullah et al. 2008 gold standard), credentialed access.
    [physionet.org](https://www.physionet.org/content/deidentifiedmedicaltext/)
50. **John Snow Labs.** Free academic licences for Spark NLP for Healthcare (incl. de-identification).
    [johnsnowlabs.com](https://johnsnowlabs.com/john-snow-labs-is-providing-free-academic-licenses-to-researchers-and-educators-in-artificial-intelligence);
    Databricks integration and trial: [docs](https://docs.azure.cn/en-us/databricks/partners/ml/john-snow-labs)

## Tools

16. **Spec Kit** (GitHub) — spec-driven development. [github.com/github/spec-kit](https://github.com/github/spec-kit)
17. **Superpowers** (obra) — Claude Code skills for planning, TDD, debugging, review. github.com/obra/superpowers
18. **Label Studio** (HumanSignal) — annotation tool. [labelstud.io](https://labelstud.io)
