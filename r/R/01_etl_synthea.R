# Full Synthea -> OMOP CDM 5.4 load with OHDSI's ETLSyntheaBuilder. This is the
# "complete CDM" path; the Python build step only populates the handful of
# tables the benchmark needs.
#
# Target database (env DENTAL_DBMS):
#   postgresql  Postgres or Lakebase (managed Postgres). Default.
#               DENTAL_DB_SERVER=<host>/<database>, DENTAL_DB_USER, DENTAL_DB_PASSWORD
#               (Lakebase: an OAuth token), DENTAL_DB_PORT (5432), DENTAL_CDM_SCHEMA (cdm),
#               DENTAL_DB_EXTRA (sslmode=require for Lakebase; set "" for a local Postgres without SSL)
#   spark       Databricks SQL warehouse (Delta tables) via the Databricks JDBC driver.
#               DENTAL_DB_CONNECTION_STRING=jdbc:databricks://..., DENTAL_DB_USER=token,
#               DENTAL_DB_PASSWORD=<token>, DENTAL_CDM_SCHEMA=<catalog>.<schema>
#
#   DENTAL_DBMS=postgresql DENTAL_DB_SERVER=localhost/postgres Rscript r/R/01_etl_synthea.R
#
# Needs: synthea/output/csv (from synthea/run_synthea.sh) and an Athena
# vocabulary download (SNOMED, LOINC, RxNorm, CDT, ...) unzipped to
# data/vocab/. Athena: https://athena.ohdsi.org (free account; CDT needs
# its separate license acknowledgement).
#
# UNTESTED in CI: depends on Java/JDBC drivers and the Athena download.

library(ETLSyntheaBuilder)

repo        <- normalizePath(".")
synthea_csv <- file.path(repo, "synthea", "output", "csv")
vocab_dir   <- file.path(repo, "data", "vocab")
env <- function(k, d = "") Sys.getenv(k, d)
dbms <- env("DENTAL_DBMS", "postgresql")
jar_dir <- env("DATABASECONNECTOR_JAR_FOLDER", file.path(path.expand("~"), "jdbc"))  # see r/install.R

cd <- switch(dbms,
  postgresql = DatabaseConnector::createConnectionDetails(
    dbms = "postgresql", server = env("DENTAL_DB_SERVER", "localhost/postgres"),
    user = env("DENTAL_DB_USER", "postgres"), password = env("DENTAL_DB_PASSWORD"),
    port = as.integer(env("DENTAL_DB_PORT", "5432")), extraSettings = env("DENTAL_DB_EXTRA", "sslmode=require"),
    pathToDriver = jar_dir),
  spark = DatabaseConnector::createConnectionDetails(
    dbms = "spark", connectionString = env("DENTAL_DB_CONNECTION_STRING"),
    user = env("DENTAL_DB_USER", "token"), password = env("DENTAL_DB_PASSWORD"), pathToDriver = jar_dir),
  stop("DENTAL_DBMS must be postgresql or spark"))
cdm_schema     <- env("DENTAL_CDM_SCHEMA", "cdm")
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
