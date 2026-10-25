# Parity checks: the R side must agree with the Python side.
#   Rscript r/tests/test_parity.R            (from repo root, after python scripts 01 + 02)
# Base R only.

source("r/R/labels.R")
source("eval/score.R")

# 0. AAP worksheet edge cases: CAL missing, tooth loss, complexity factors.
if (file.exists("data/labels/aap_rule_cases.csv")) {
  g <- read.csv("data/labels/aap_rule_cases.csv", stringsAsFactors = FALSE)
  r <- label_chart(g$pd, rep(30, nrow(g)), g$cal, g$rbl, g$lost, vertical_defect_mm = g$vd,
                   furcation_class = g$fc, mobility_degree = g$mob, remaining_teeth = g$rem)
  cat(sprintf("AAP rules: %d / %d edge cases agree\n", sum(r == g$label), nrow(g)))
  stopifnot(all(r == g$label))
} else cat("AAP rules: skipped (run python/scripts/export_rules_predictions.py first)\n")

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
  num <- c("coverage", "pct_agree_consensus", "kappa_vs_consensus", "weighted_kappa_vs_consensus",
           "mean_kappa_vs_each_reviewer", "unsafe_rate", "s2_rate")
  d <- max(abs(as.matrix(r[num]) - as.matrix(py[num])), na.rm = TRUE)
  cat(sprintf("reliability: max |R - Python| = %.2e over %d methods\n", d, nrow(py)))
  stopifnot(d < 1e-9)
  # spec 002: agreement by difficulty level
  py_lv <- read.csv("data/review/simulated_reliability/by_level.csv", stringsAsFactors = FALSE)
  cons_df <- read.csv("data/review/simulated_reliability/consensus.csv", stringsAsFactors = FALSE)
  r_lv <- by_level(key, cons_df, compare)
  m <- merge(py_lv, r_lv, by = c("method", "level"), suffixes = c("_py", "_r"))
  dl <- max(abs(m$pct_agree_consensus_py - m$pct_agree_consensus_r), na.rm = TRUE)
  cat(sprintf("by level:    max |R - Python| = %.2e over %d rows\n", dl, nrow(m)))
  stopifnot(nrow(m) == nrow(py_lv), dl < 1e-9)
  # 4b. AI vs humans: point estimates exact, bootstrap CI approximate (different RNG)
  py_vh_f <- "data/review/simulated_reliability/agreement_vs_humans.csv"
  if (file.exists(py_vh_f)) {
    py_vh <- read.csv(py_vh_f, stringsAsFactors = FALSE)
    w <- reshape(labels[, c("visit_id", "reviewer", "status")], idvar = "visit_id", timevar = "reviewer", direction = "wide")
    rownames(w) <- w$visit_id; w$visit_id <- NULL; names(w) <- sub("^status\\.", "", names(w))
    w <- w[order(as.numeric(rownames(w))), , drop = FALSE]
    r_vh <- agreement_vs_humans(w, compare, n_boot = 200)
    mm <- merge(py_vh, r_vh, by = "rater", suffixes = c(".py", ".r"))
    d <- max(abs(mm$mean_kappa_vs_humans.py - mm$mean_kappa_vs_humans.r))
    ci_d <- max(abs(c(mm$ci_low.py - mm$ci_low.r, mm$ci_high.py - mm$ci_high.r)), na.rm = TRUE)
    cat(sprintf("vs humans:   max |R - Python| = %.2e over %d raters; CI bounds within %.3f\n", d, nrow(mm), ci_d))
    stopifnot(nrow(mm) == nrow(py_vh), d < 1e-9, ci_d < 0.05)
  }
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

# 6. Judge bake-off kappa (spec 002).
py_bo <- "data/corpus/simulated_judge_bakeoff.csv"
if (file.exists(py_bo) && file.exists("data/corpus/simulated_judgments_gold_all_candidates.csv")) {
  if (!exists("judge_kappa")) source("r/R/05_cost_effectiveness.R")
  bo <- read.csv(py_bo, stringsAsFactors = FALSE)
  all <- read.csv("data/corpus/simulated_judgments_gold_all_candidates.csv", stringsAsFactors = FALSE)
  rk <- sapply(bo$judge_model, function(j) judge_kappa(all[all$judge_model == j, ]))
  d <- max(abs(rk - bo$kappa))
  cat(sprintf("judge bake-off: max |R - Python| kappa = %.2e over %d judges\n", d, nrow(bo)))
  stopifnot(d < 1e-9)
}
cat("parity OK (incl. cost-effectiveness and judge bake-off)\n")
