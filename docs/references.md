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

## Tools

16. **Spec Kit** (GitHub) — spec-driven development. [github.com/github/spec-kit](https://github.com/github/spec-kit)
17. **Superpowers** (obra) — Claude Code skills for planning, TDD, debugging, review. github.com/obra/superpowers
18. **Label Studio** (HumanSignal) — annotation tool. [labelstud.io](https://labelstud.io)
