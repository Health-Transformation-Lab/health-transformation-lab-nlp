# One-time setup for the R side. Run from the repo root:  Rscript r/install.R
# Base-R pieces (labels.R, eval/score.R, tests/test_parity.R) need none of this.

cran <- c(
  "tidymodels",   # baselines: multinom_reg, workflows, rsample
  "textrecipes",  # TF-IDF step for the text baseline
  "glmnet",       # engine for penalised multinomial regression
  "readr", "dplyr", "yaml",
  "text",         # Hugging Face encoders from R (torch via reticulate); see 03_encoders.R
  "remotes", "DatabaseConnector"
)
install.packages(setdiff(cran, rownames(installed.packages())))

# OHDSI ETL for Synthea -> OMOP CDM (not on CRAN).
remotes::install_github("OHDSI/ETL-Synthea")
remotes::install_github("OHDSI/CommonDataModel")

# JDBC drivers for the OMOP database: Postgres / Lakebase, and Databricks SQL.
jar_dir <- Sys.getenv("DATABASECONNECTOR_JAR_FOLDER", file.path(path.expand("~"), "jdbc"))
dir.create(jar_dir, showWarnings = FALSE, recursive = TRUE)
Sys.setenv(DATABASECONNECTOR_JAR_FOLDER = jar_dir)
DatabaseConnector::downloadJdbcDrivers("postgresql", pathToDriver = jar_dir)
DatabaseConnector::downloadJdbcDrivers("spark", pathToDriver = jar_dir)
message("Set DATABASECONNECTOR_JAR_FOLDER=", jar_dir, " in your .Renviron")

# The `text` package needs a Python env with torch + transformers the first time:
#   text::textrpp_install()      # creates a conda env; one-time, several minutes
#   text::textrpp_initialize(save_profile = TRUE)
message("R setup done. For encoder rungs run text::textrpp_install() once.")
