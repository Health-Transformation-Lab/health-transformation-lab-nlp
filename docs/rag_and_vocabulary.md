# Retrieval, OMOP vocabulary and graphs: ideas to test

> Personal learning project; exploratory; synthetic data only.

The note readers today use rules, TF-IDF, encoders or an LLM on the note
alone. Published work suggests adding structured knowledge (OMOP's concept
hierarchy, relationships and synonyms, or a graph of the patient's record) can
raise accuracy. This page lists what to try here and how to test each idea with
the repo's existing measures: agreement and kappa vs reviewers, the
**AI-vs-human acceptance test**, results by difficulty level (L1 stated / L2
translate / L3 infer), unsafe-error rate, and cost.

## What the evidence says (public sources)

| Work | What they did | Finding |
|---|---|---|
| Lee, Liu, …, Ryan, Ta, Weng (Columbia), medRxiv 2020 | Concept embeddings learned from OMOP **knowledge graphs** (hierarchy, enriched relations) vs from EHR co-occurrence, for finding eMERGE phenotype concepts | Graph-based embeddings beat EHR-based ones (Recall@500 0.64 enriched graph, 0.61 hierarchical, vs 0.51 and 0.46 for EHR) |
| Ahmed, Soby, Aasman, Mirhaji (Montefiore), OHDSI 2025 | OMOP concept mapping: vector retrieval of candidates, then graph expansion over `CONCEPT_RELATIONSHIP`, `CONCEPT_ANCESTOR` and `CONCEPT_SYNONYM`, then LLM agents filter | 48% exact match to manual mappings on 100 lab terms, 70% within the top candidates, about $5 inference; no baseline numbers reported |
| Thio, Lewis, Denaxas, Dobson (UCL), arXiv 2025 (MediGRAF) | Patient records as a **Neo4j graph** (text-to-Cypher) plus vector search over notes, merged for an LLM | Hybrid answered 100% of simple and medium questions vs 80% and 52% for graph-only; small study (10 patients) |
| Zhao et al., arXiv 2025 (MedRAG) | Hierarchical diagnostic knowledge graph combined with retrieved similar EHRs | Reported fewer misdiagnoses than RAG baselines (see paper for figures) |
| Schuemie, Ostropolets et al., npj Digit Med 2025 (KEEPER) | Standardized structured patient profile from OMOP, reviewed by humans and LLMs | LLM agreement with humans comparable to human–human ([process.md](process.md#validation-criterion-as-reliable-as-a-human-reviewer)) |

None of these are dental. Dental vocabulary coverage in OMOP is thin (see
[omop_dental_vs_medical.md](omop_dental_vs_medical.md)), so expect to add local
concepts and synonyms.

## OMOP pieces to use

| Table | Use |
|---|---|
| `CONCEPT_SYNONYM` | Alternate names: "chronic periodontitis", "periodontitis, chronic", abbreviations. Expand rule patterns and retrieval queries |
| `CONCEPT_ANCESTOR` | Pre-computed transitive closure of the hierarchy. "Is this code any kind of periodontitis?" is one join, with no hand list of codes. Also roll up to a common parent |
| `CONCEPT_RELATIONSHIP` | Maps to standard (ICD-10 K05.3x → SNOMED), "has finding site", CDT and HCPCS links |
| `DENTAL_LOCAL` concepts (`omop/vocab/local_concepts.csv`) | Fill dental gaps: stage/grade terms, perio chart measures, note shorthand ("gen mod perio", "SRP x4") |

`CONCEPT_ANCESTOR` already stores every ancestor–descendant pair, so most
hierarchy questions are plain SQL joins. A graph database earns its place for
multi-hop questions over the **patient** record (person → visits → teeth →
sites → measurements over time), not for the vocabulary alone.

## Retrieval techniques

| Technique | Good at | In this repo |
|---|---|---|
| Lexical (BM25, synonym-expanded) | Exact codes, abbreviations, numbers | add; cheap baseline |
| Dense embeddings | Paraphrase, typos | SapBERT (concept names) and GTE-ModernColBERT (late interaction) are already in `models.yaml` as non-classifier models |
| Hybrid lexical + dense, then rerank | Best of both | add |
| Graph expansion (ancestors, descendants, relationships) | Normalizing to the right level; codes the reader hasn't seen | `CONCEPT_ANCESTOR` joins; NetworkX for experiments |
| Example retrieval (kNN few-shot) | Giving an LLM the most similar labeled notes instead of random ones | MedGemma reader `--shots` currently picks at random |
| Patient-graph retrieval (GraphRAG) | Multi-visit questions (grade from progression) | needs OMOP `SITE` / `SITE_EVENT` and visits |

## Test cases

Each is an experiment against the same review charts and the acceptance test.
"Win" is decided in advance.

| # | Idea | Compare | Expected to help | Win if |
|---|---|---|---|---|
| R1 | **Synonym-expanded note rules**: add `CONCEPT_SYNONYM` + local dental synonyms to `note_reader` patterns | `note_rules` vs `note_rules+syn` | L2 (translate) notes: pre-2017 terms, abbreviations, typos | L2 agreement up; L1 not down; acceptance verdict no worse |
| R2 | **Ancestor-based code readers**: classify diagnosis and procedure codes by `CONCEPT_ANCESTOR` instead of hard-coded lists | hard-coded vs ancestor reader on `proc_dx_*` | Codes the list missed; new code versions | Coverage up with no drop in agreement |
| R3 | **Vocabulary-grounded LLM reader**: retrieve top-k OMOP concepts (with ancestors and definitions) for the note's terms and add them to the MedGemma prompt | `reader-v2` vs `reader-v2+vocab` | L2 and L3 | Agreement up on L2/L3; gate-fail rate not up |
| R4 | **kNN few-shot**: retrieve the most similar training notes (dense or ColBERT) as examples | random shots vs kNN shots, same k | Unusual note styles | Acceptance diff up; prompt-variant sensitivity down |
| R5 | **Concept-normalized features for the encoders**: append normalized concept ids or labels to the note text before fine-tuning | BERT rung vs BERT+concepts | Small data, many surface forms | Agreement up at equal training size |
| R6 | **KEEPER-style structured profile**: build a standardized profile from OMOP (codes, perio chart measures, radiograph AI, risk factors) for the LLM and as a reviewer view | note-only LLM vs profile LLM vs profile+note | L3 (no or conflicting written dx) | L3 agreement up; acceptance test non-inferior |
| R7 | **Patient-graph grade**: graph or recursive-SQL retrieval of prior visits' bone level, for the direct-evidence grade rule | indirect grade (%RBL/age) vs direct evidence when available | Grade accuracy | Grade kappa vs reviewers up |
| R8 | **Graph vs SQL**: same R2/R7 queries in Postgres (`CONCEPT_ANCESTOR` joins, recursive CTE) vs a graph DB | latency, code size, cost | Engineering choice | Graph DB only if it is simpler or faster for R7 |

For every test, record: agreement and kappa vs reviewers, the acceptance
verdict, by-level results, unsafe rate, gate-fail and fallback rates (LLM),
tokens per note, and cost per million notes in the
[financial trade-offs](financial_tradeoffs.md) table.

## What's needed first

- OMOP vocabularies from Athena (not in the repo; licensing per vocabulary) plus
  dental local concepts and synonyms.
- A small vector store: Lakebase Search or Databricks AI Search (Free Edition:
  one endpoint), or FAISS locally. See [results_storage.md](results_storage.md).
- Synthetic notes with more L2 surface variation (the MedGemma paraphraser idea)
  so R1/R3/R4 have something to improve on.

## Sources

- Lee J, Liu C, et al. *Comparative effectiveness of knowledge graphs- and EHR data-based medical concept embedding for phenotyping.* medRxiv 2020. [link](https://www.medrxiv.org/content/10.1101/2020.07.14.20151274v1.abstract)
- Ahmed A, Soby S, Aasman B, Mirhaji P. *Automated OMOP concept mapping using multi-agent LLMs and graph-enhanced semantic retrieval.* OHDSI Symposium 2025. [PDF](https://www.ohdsi.org/wp-content/uploads/2025/10/508-Ahmed-Automated-OMOP-Concept-Mapping-Using-Multi-Agent-Large-Language-Models-and-Graph-Enhanced-Semantic-Retrieval-Report-Adil-Ahmed.pdf)
- Thio S, Lewis M, Denaxas S, Dobson RJB. *Unlocking electronic health records: a hybrid graph RAG approach to safe clinical AI for patient QA.* arXiv 2602.00009. [link](https://www.arxiv.org/abs/2602.00009)
- Zhao X, Liu S, Yang S-Y, Miao C. *MedRAG: enhancing retrieval-augmented generation with knowledge graph-elicited reasoning for healthcare copilot.* arXiv 2502.04413. [link](https://arxiv.org/abs/2502.04413v2)
- Schuemie MJ, Ostropolets A, et al. *Standardized patient profile review using large language models for case adjudication in observational research.* npj Digital Medicine 2025. [doi](https://doi.org/10.1038/s41746-025-01433-4)
