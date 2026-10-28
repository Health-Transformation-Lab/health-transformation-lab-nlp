# Cost-effectiveness in R. Twin of python/health_transformation_lab_nlp/cost_effectiveness.py:
# judge calibration on the human-reviewed charts, Rogan-Gladen corrected accuracy,
# bootstrap CI (judge uncertainty included), cost per 1,000 correct notes, dominance
# and ICER along the frontier. Point estimates, costs and the frontier match Python
# exactly (r/tests/test_parity.R); bootstrap CIs differ by random stream only.
#
#   Rscript r/R/05_cost_effectiveness.R             # real judgments
#   Rscript r/R/05_cost_effectiveness.R simulated   # dry run
# Base R only. Reads data/corpus/*judgments_*.csv and cost_benchmark.csv.

calibrate_judge <- function(gold) {
  g <- gold[gold$verdict %in% c("correct", "incorrect") & as.logical(gold$gate_ok), ]
  tc <- as.logical(g$truly_correct)
  list(sensitivity = mean(g$verdict[tc] == "correct"),
       specificity = mean(g$verdict[!tc] == "incorrect"),
       n_pos = sum(tc), n_neg = sum(!tc),
       nd_rate = mean(gold$verdict == "not_determinable"))
}

# spec 002: judge bake-off statistic (Cohen's kappa, verdict vs truth on the calibration set)
judge_kappa <- function(gold) {
  g <- gold[gold$verdict %in% c("correct", "incorrect") & as.logical(gold$gate_ok), ]
  a <- g$verdict == "correct"; b <- as.logical(g$truly_correct)
  po <- mean(a == b); pe <- mean(a) * mean(b) + mean(!a) * mean(!b)
  if (pe == 1) NA_real_ else (po - pe) / (1 - pe)
}

rogan_gladen <- function(p, sens, spec) {
  d <- sens + spec - 1
  if (!is.finite(d) || d <= 0) return(NA_real_)
  min(max((p + spec - 1) / d, 0), 1)
}

p_judged_correct <- function(s) {
  d <- s[s$verdict %in% c("correct", "incorrect") & as.logical(s$gate_ok), ]
  if (!nrow(d)) NA_real_ else mean(d$verdict == "correct")
}

corrected_accuracy <- function(sample, gold, n_boot = 1000, seed = 0) {
  cal <- calibrate_judge(gold)
  est <- rogan_gladen(p_judged_correct(sample), cal$sensitivity, cal$specificity)
  set.seed(seed)
  boots <- replicate(n_boot, {
    s <- sample[sample.int(nrow(sample), replace = TRUE), ]
    g <- gold[sample.int(nrow(gold), replace = TRUE), ]
    c <- calibrate_judge(g)
    rogan_gladen(p_judged_correct(s), c$sensitivity, c$specificity)
  })
  ci <- stats::quantile(boots, c(0.025, 0.975), na.rm = TRUE, names = FALSE)
  data.frame(p_judged_correct = p_judged_correct(sample), accuracy_est = est,
             ci_low = ci[1], ci_high = ci[2])
}

frontier <- function(t, n_notes) {
  t <- t[order(t$cost_usd, -t$accuracy_est), ]
  best <- -1; t$dominated <- FALSE
  for (i in seq_len(nrow(t))) {
    if (t$accuracy_est[i] <= best) t$dominated[i] <- TRUE else best <- t$accuracy_est[i]
  }
  t$icer_usd_per_extra_correct_note <- NA_real_; t$compared_to <- ""
  prev <- NA
  for (i in which(!t$dominated)) {
    if (!is.na(prev)) {
      t$icer_usd_per_extra_correct_note[i] <- (t$cost_usd[i] - t$cost_usd[prev]) /
        ((t$accuracy_est[i] - t$accuracy_est[prev]) * n_notes)
      t$compared_to[i] <- t$method[prev]
    }
    prev <- i
  }
  t$expected_correct_notes <- t$accuracy_est * n_notes
  t$usd_per_1k_correct <- t$cost_usd / (t$expected_correct_notes / 1000)
  t
}

cost_effectiveness <- function(gold, corp, bench, n_notes) {
  rows <- lapply(split(corp, corp$method), function(s) {
    m <- s$method[1]
    cbind(method = m, corrected_accuracy(s, gold), cost_usd = bench$cost_usd[bench$method == m])
  })
  frontier(do.call(rbind, rows), n_notes)
}

if (sys.nframe() == 0) {
  sim <- identical(commandArgs(trailingOnly = TRUE)[1], "simulated")
  prefix <- if (sim) "simulated_" else ""
  gold <- read.csv(file.path("data/corpus", paste0(prefix, "judgments_gold.csv")), stringsAsFactors = FALSE)
  corp <- read.csv(file.path("data/corpus", paste0(prefix, "judgments_corpus.csv")), stringsAsFactors = FALSE)
  bench <- read.csv("data/corpus/cost_benchmark.csv", stringsAsFactors = FALSE)
  meta <- readLines("data/corpus/corpus_meta.json", warn = FALSE)
  n_notes <- as.numeric(sub('.*"corpus_notes": *([0-9]+).*', "\\1", paste(meta, collapse = "")))
  cal <- calibrate_judge(gold)
  t <- cost_effectiveness(gold, corp, bench, n_notes)
  write.csv(t, file.path("data/corpus", paste0(prefix, "cost_effectiveness_R.csv")), row.names = FALSE)
  if (sim) cat("*** SIMULATED: dry run, not a result ***\n")
  cat(sprintf("judge: sensitivity %.3f, specificity %.3f (n=%d+%d)\n",
              cal$sensitivity, cal$specificity, cal$n_pos, cal$n_neg))
  print(t[, c("method", "accuracy_est", "ci_low", "ci_high", "cost_usd", "usd_per_1k_correct",
              "dominated", "icer_usd_per_extra_correct_note", "compared_to")], digits = 4, row.names = FALSE)
}
