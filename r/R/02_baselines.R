# Baseline rungs in tidymodels. Each returns list(pred = chr, proba = n x 6 matrix | NULL)
# with proba columns in PERIO_LABELS order, ready for score_run().

suppressPackageStartupMessages({
  library(tidymodels)
  library(textrecipes)
})

.as_factor <- function(df) { df$label <- factor(df$label, levels = PERIO_LABELS); df }

.proba_matrix <- function(fit, test) {
  p <- predict(fit, test, type = "prob")
  m <- matrix(0, nrow(test), length(PERIO_LABELS), dimnames = list(NULL, PERIO_LABELS))
  for (l in PERIO_LABELS) { col <- paste0(".pred_", l); if (col %in% names(p)) m[, l] <- p[[col]] }
  m
}

rung_structured <- function(train, test) {
  rec <- recipe(label ~ max_probing_depth_mm + bop_pct + max_cal_mm + rbl_pct + teeth_lost_perio,
                data = .as_factor(train)) |> step_normalize(all_numeric_predictors())
  fit <- workflow(rec, multinom_reg() |> set_engine("nnet", MaxNWts = 5000)) |> fit(.as_factor(train))
  proba <- .proba_matrix(fit, test)
  list(pred = PERIO_LABELS[max.col(proba, ties.method = "first")], proba = proba)
}

rung_tfidf <- function(train, test) {
  rec <- recipe(label ~ note_text, data = .as_factor(train)) |>
    step_tokenize(note_text, token = "ngrams", options = list(n = 2, n_min = 1)) |>
    step_tokenfilter(note_text, min_times = 2, max_tokens = 3000) |>
    step_tfidf(note_text)
  fit <- workflow(rec, multinom_reg(penalty = 0.001, mixture = 0) |> set_engine("glmnet")) |>
    fit(.as_factor(train))
  proba <- .proba_matrix(fit, test)
  list(pred = PERIO_LABELS[max.col(proba, ties.method = "first")], proba = proba)
}
