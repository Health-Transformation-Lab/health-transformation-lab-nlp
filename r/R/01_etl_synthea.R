# Full Synthea -> OMOP CDM 5.4 load with OHDSI's ETLSyntheaBuilder, into a
# local DuckDB file. This is the "complete CDM" path; the Python build step
# only populates the handful of tables the benchmark needs.
#
#   Rscript r/R/01_etl_synthea.R
#
# Needs: synthea/output/csv (from synthea/run_synthea.sh) and an Athena
# vocabulary download (SNOMED, LOINC, RxNorm, CDT, ...) unzipped to
# data/vocab/. Athena: https://athena.ohdsi.org (free account; CDT needs
# its separate license acknowledgement).
#
# UNTESTED in CI: depends on Java/JDBC drivers and the Athena download.

library(ETLSyntheaBuilder)

repo        <- normalizePath(".")
db_file     <- file.path(repo, "data", "omop", "cdm.duckdb")
synthea_csv <- file.path(repo, "synthea", "output", "csv")
vocab_dir   <- file.path(repo, "data", "vocab")
dir.create(dirname(db_file), recursive = TRUE, showWarnings = FALSE)

cd <- DatabaseConnector::createConnectionDetails(dbms = "duckdb", server = db_file)
cdm_schema     <- "main"      # DuckDB: one schema is fine for a sandbox
synthea_schema <- "native"
cdm_version    <- "5.4"
synthea_version <- "3.3.0"    # match the jar run_synthea.sh downloaded

ETLSyntheaBuilder::CreateCDMTables(cd, cdmSchema = cdm_schema, cdmVersion = cdm_version)
ETLSyntheaBuilder::CreateSyntheaTables(cd, syntheaSchema = synthea_schema, syntheaVersion = synthea_version)
ETLSyntheaBuilder::LoadSyntheaTables(cd, syntheaSchema = synthea_schema, syntheaFileLoc = synthea_csv)
ETLSyntheaBuilder::LoadVocabFromCsv(cd, cdmSchema = cdm_schema, vocabFileLoc = vocab_dir)
ETLSyntheaBuilder::LoadEventTables(cd, cdmSchema = cdm_schema, syntheaSchema = synthea_schema,
                                   cdmVersion = cdm_version, syntheaVersion = synthea_version)

# Dental extension: SITE, SITE_EVENT, perio_chart view + DENTAL_LOCAL concepts.
conn <- DatabaseConnector::connect(cd)
sql <- readLines(file.path(repo, "omop", "ddl", "dental_extension.sql"))
for (stmt in strsplit(paste(sql[!grepl("^\\s*--", sql)], collapse = "\n"), ";")[[1]]) {
  if (nzchar(trimws(stmt))) DatabaseConnector::executeSql(conn, stmt)
}
local <- read.csv(file.path(repo, "omop", "vocab", "local_concepts.csv"), stringsAsFactors = FALSE)
local$invalid_reason <- NA
DatabaseConnector::insertTable(conn, tableName = "concept", data = local,
                               dropTableIfExists = FALSE, createTable = FALSE)
DatabaseConnector::disconnect(conn)
message("CDM loaded: ", db_file)
