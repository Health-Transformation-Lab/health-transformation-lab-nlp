# Feature Specification: Site-level periodontal data, derived measures and OMOP storage designs

**Feature Branch**: `006-site-level-omop`

**Created**: 2026-10-25

**Status**: v1 implemented on synthetic data

**Input**: "Represent tooth- and site-level periodontal measurements in OMOP, compute
the derived measures the classifications need, and test which storage design works."

> Personal learning project; synthetic data; public sources only.

## Context

Dental charts record probing depth, attachment loss and bleeding at six sites
on each tooth, plus missing teeth, furcation and mobility per tooth. The
classifications (2017 AAP/EFP staging; 2012 CDC/AAP surveillance definitions)
need **derived** person-visit measures: maxima, counts of sites over a
threshold, and counts of *different teeth*. OMOP has concepts for many raw
observations and for final diagnoses, but few for the intermediate measures,
and no standard way to say which tooth or site a row applies to.

## User stories

### US1 - Site-level synthetic charts (P1)
32 teeth × 6 sites (MB, B, DB, ML, L, DL) per exam: PD, CAL, bleeding; per tooth:
present/missing (and why), furcation, mobility. Generated from each visit's chart
so that the derived measures reproduce it.
- **Given** a visit, **Then** the max interproximal CAL, max PD and teeth lost to
  periodontitis from the sites equal the visit chart, and the BOP share falls on
  the same side of 10%.
- **Then** the 2017 stage computed from the site-derived measures equals the stage
  of the visit's chart.

### US2 - Derived-measure layer and two classifications (P1)
One function / view computes per exam: max PD, max interproximal CAL, % sites
bleeding, teeth present, teeth lost to perio, % teeth with interproximal CAL ≥ 1,
counts of different teeth with interproximal CAL ≥ 3/4/6 and PD ≥ 4/5, sites with
PD ≥ 5, max furcation, max mobility. From these: 2017 AAP/EFP stage and 2012 CDC/AAP
category. Python = R = SQL (Postgres).

### US3 - Three storage designs compared (P1)
Same mouths stored three ways in Postgres (Lakebase):
- **A. Post-coordinated** (OHDSI Dentistry WG): MEASUREMENT row per site and measure,
  linked to SITE (tooth, tooth-site) through SITE_EVENT.
- **B. Pre-coordinated**: one local concept per measure × tooth × site in
  MEASUREMENT; decoded via CONCEPT.
- **C. Site columns** (site-aware MEASUREMENT, as proposed for dental OMOP):
  `tooth_number`, `tooth_site` columns on a MEASUREMENT extension.
Measure: identical derived results, SQL size, joins, query time, storage.

### US4 - Concept mapping and Atlas feasibility (P2)
Table of raw and derived measures: standard concept found or not, proposed local
concept otherwise. Which classification criteria an Atlas cohort can express
directly, and which only after the derived layer is written back as MEASUREMENT rows.

## Requirements
- FR-001 `sites.py` (generate, derive, CDC/AAP); R twin; SQL views per design.
- FR-002 `site_designs.py` loads A/B/C into Postgres and benchmarks them.
- FR-003 derived measures written back as MEASUREMENT rows with local concepts (design C).
- FR-004 docs/site_level_omop.md: designs, results, mapping table, Atlas feasibility.

## Success criteria
- SC-001 Tests: site-chart consistency; CDC/AAP rules; Python = R = SQL on all designs.
- SC-002 CI runs the Postgres comparison.

## Assumptions
- Site values are synthetic and only constrained to reproduce the chart; their
  distribution within a mouth is a placeholder.
- ADA standard 1084 is not public; mapping from it is out of scope (action item).
