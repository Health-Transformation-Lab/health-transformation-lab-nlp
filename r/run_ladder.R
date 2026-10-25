# Run rungs from R and score them with eval/score.R.
#
#   Rscript r/run_ladder.R rules_baseline structured_baseline tfidf_logreg
#   Rscript r/run_ladder.R distilbert-base+frozen      # embeddings + glmnet
#   Rscript r/run_ladder.R distilbert-base+finetune    # calls the Python trainer via reticulate
#
# Reads data/labels/labeled_notes.csv and split.csv written by the Python
# build + split steps (or by the R ETL path), so both languages use the same
# notes and the same patient split. Run from the repo root.

source("r/R/labels.R")
source("eval/score.R")

rungs <- commandArgs(trailingOnly = TRUE)
if (!length(rungs)) rungs <- c("rules_baseline", "structured_baseline", "tfidf_logreg")

notes <- read.csv("data/labels/labeled_notes.csv", stringsAsFactors = FALSE)
df <- merge(notes, read.csv("data/labels/split.csv"))
train <- df[df$split == "train", ]; test <- df[df$split == "test", ]
cat(sprintf("train=%d test=%d\n", nrow(train), nrow(test)))

needs_tidymodels <- any(rungs != "rules_baseline")
if (needs_tidymodels) source("r/R/02_baselines.R")
if (any(grepl("\\+(frozen|finetune)$", rungs))) source("r/R/03_encoders.R")
reg <- if (requireNamespace("yaml", quietly = TRUE)) yaml::read_yaml("models.yaml") else NULL

summary <- list()
for (rung in rungs) {
  res <- switch(rung,
    rules_baseline      = rung_rules(train, test),
    structured_baseline = rung_structured(train, test),
    tfidf_logreg        = rung_tfidf(train, test),
    {
      base <- sub("\\+(frozen|finetune)$", "", rung)
      m <- Filter(function(x) x$id == base, reg$models)[[1]]
      if (endsWith(rung, "+finetune")) rung_encoder_finetune(train, test, base)
      else rung_encoder_frozen(train, test, m$hf)
    })
  s <- score_run(test$label, res$pred, res$proba, model_id = rung)
  cat(rung, ": wrote ", write_run(s, "data/results"), "\n", sep = "")
  summary[[rung]] <- setNames(s$value[s$class == ""], s$metric[s$class == ""])
}
print(round(do.call(rbind, summary), 3))
