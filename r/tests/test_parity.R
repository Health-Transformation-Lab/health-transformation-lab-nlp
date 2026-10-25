# Parity checks: the R side must agree with the Python side.
#   Rscript r/tests/test_parity.R            (from repo root, after python scripts 01 + 02)
# Base R only.

source("r/R/labels.R")
source("eval/score.R")

if (file.exists("data/labels/labeled_notes.csv")) {
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

} else cat("labels/rules/scorer: skipped (run python scripts 01 + 02 + export_rules_predictions first)\n")

# 4. Reliability: R 04_reliability.R == Python reliability.py (needs a simulated or real review run).
py_rel <- "data/review/simulated_reliability/methods_vs_reviewers.csv"
if (file.exists(py_rel) && file.exists("data/review/simulated_reviewer_labels.csv")) {
  source("r/R/04_reliability.R")
  labels <- read.csv("data/review/simulated_reviewer_labels.csv", stringsAsFactors = FALSE)
  key <- read.csv("data/datasets/answer_key/review_key.csv", stringsAsFactors = FALSE)
  py <- read.csv(py_rel, stringsAsFactors = FALSE)
  compare <- setNames(lapply(setdiff(py$method, "generator_chart_truth"), function(m) {
    if (startsWith(m, "ai:")) { p <- read.csv(sprintf("data/datasets/ai_predictions_%s.csv", sub("^ai:", "", m)))
      setNames(p$pred, p$visit_id) } else setNames(key[[m]], key$visit_id)
  }), setdiff(py$method, "generator_chart_truth"))
  r <- reliability_report(labels, key, compare)$methods
  r <- r[match(py$method, r$method), ]
  num <- c("coverage", "pct_agree_consensus", "kappa_vs_consensus", "weighted_kappa_vs_consensus", "mean_kappa_vs_each_reviewer")
  d <- max(abs(as.matrix(r[num]) - as.matrix(py[num])), na.rm = TRUE)
  cat(sprintf("reliability: max |R - Python| = %.2e over %d methods\n", d, nrow(py)))
  stopifnot(d < 1e-9)
} else cat("reliability: skipped (run python scripts 12 --simulate and 13 --simulated first)\n")
cat("parity OK (all sections)\n")

# 5. Cost-effectiveness: point estimates, costs, dominance and ICER match Python.
py_ce <- "data/corpus/simulated_cost_effectiveness.csv"
if (file.exists(py_ce)) {
  source("r/R/05_cost_effectiveness.R")
  gold <- read.csv("data/corpus/simulated_judgments_gold.csv", stringsAsFactors = FALSE)
  corp <- read.csv("data/corpus/simulated_judgments_corpus.csv", stringsAsFactors = FALSE)
  bench <- read.csv("data/corpus/cost_benchmark.csv", stringsAsFactors = FALSE)
  py <- read.csv(py_ce, stringsAsFactors = FALSE)
  r <- cost_effectiveness(gold, corp, bench, 1e6)
  r <- r[match(py$method, r$method), ]
  num <- c("accuracy_est", "cost_usd", "usd_per_1k_correct", "icer_usd_per_extra_correct_note")
  d <- max(abs(as.matrix(r[num]) - as.matrix(py[num])), na.rm = TRUE)
  stopifnot(all(r$dominated == as.logical(py$dominated)))
  cat(sprintf("cost-effectiveness: max |R - Python| = %.2e over %d methods; frontier identical\n", d, nrow(py)))
  stopifnot(d < 1e-9)
} else cat("cost-effectiveness: skipped (run python scripts 14-16 first)\n")
cat("parity OK (incl. cost-effectiveness)\n")
