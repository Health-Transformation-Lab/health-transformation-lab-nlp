# Parity checks: the R side must agree with the Python side.
#   Rscript r/tests/test_parity.R            (from repo root, after python scripts 01 + 02)
# Base R only.

source("r/R/labels.R")
source("eval/score.R")

notes <- read.csv("data/labels/labeled_notes.csv", stringsAsFactors = FALSE)
split <- read.csv("data/labels/split.csv")

# 1. Labels: R label_chart on the chart columns == Python's label column.
r_lab <- with(notes, label_chart(max_probing_depth_mm, bop_pct, max_cal_mm, rbl_pct, teeth_lost_perio))
mism <- sum(r_lab != notes$label)
cat(sprintf("labels:  %d / %d agree\n", nrow(notes) - mism, nrow(notes)))
stopifnot(mism == 0)

# 2. Rules baseline: R regex rules == Python regex rules on every note.
py_rules_file <- "data/labels/python_rules_predictions.csv"
if (file.exists(py_rules_file)) {
  py <- read.csv(py_rules_file, stringsAsFactors = FALSE)
  m <- merge(py, data.frame(note_id = notes$note_id, r_pred = rules_predict(notes$note_text)))
  cat(sprintf("rules:   %d / %d agree\n", sum(m$pred == m$r_pred), nrow(m)))
  stopifnot(all(m$pred == m$r_pred))
} else cat("rules:   skipped (run python/scripts/export_rules_predictions.py first)\n")

# 3. Scorer: R score_run == Python score.py on the same predictions.
test <- merge(notes, split)[merge(notes, split)$split == "test", ]
res <- score_run(test$label, rules_predict(test$note_text), NULL, "rules_baseline", run_id = "parity")
py_res_file <- "data/labels/python_rules_score.csv"
if (file.exists(py_res_file)) {
  py <- read.csv(py_res_file, stringsAsFactors = FALSE)
  key <- function(d) paste(d$metric, ifelse(is.na(d$class), "", d$class))
  both <- merge(data.frame(k = key(res), r = res$value), data.frame(k = key(py), p = py$value))
  diff <- abs(both$r - both$p); diff[is.na(diff)] <- 0
  cat(sprintf("scorer:  max |R - Python| = %.2e over %d metrics\n", max(diff), nrow(both)))
  stopifnot(max(diff) < 1e-9)
} else cat("scorer:  skipped (python score file not found)\n")

cat("parity OK\n")
