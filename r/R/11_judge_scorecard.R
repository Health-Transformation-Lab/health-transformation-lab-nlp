# Judge scorecard in R (spec 012). Twin of python/dental_omop_nlp/judge_scorecard.py: every README
# phenotyping metric per system against the truth and against the judge's own status, and the
# judge's agreement with the truth. Point estimates match Python exactly (r/tests/test_parity.R);
# the 95% ranges (bootstrap) and judge-corrected accuracy are Python's.
#
#   Rscript r/R/11_judge_scorecard.R              # data/datasets/judge/judge_*.csv (LLM judge)
#   Rscript r/R/11_judge_scorecard.R simulated    # the simulated dry run
# Base R only. Reads data/datasets/judge/{prefix}{chart_answers,judgments}.csv and the answer key.

if (!exists("unsafe_rates")) source("r/R/04_reliability.R")
if (!exists("score_run")) source("eval/score.R")

JUDGE_LEVELS <- c("L1", "L2", "L3")
JUDGE_METRICS <- c("exact_status", "sensitivity", "specificity", "ppv", "npv", "stage4_caught",
                   "unsafe_rate", paste0("exact_", JUDGE_LEVELS))

# Every metric for one system's answers p against reference ref (aligned; ref has no NA).
judge_point <- function(ref, p, level) {
  ok <- !is.na(p) & p == ref                     # no status is wrong, as in the README
  s4 <- ref == "periodontitis_stage_4"
  sc <- score_run(ref, ifelse(is.na(p), "none", p), model_id = "judge", run_id = "judge")
  yn <- setNames(sc$value[sc$class == ""], sc$metric[sc$class == ""])
  out <- c(exact_status = mean(ok), sensitivity = yn[["sensitivity"]], specificity = yn[["specificity"]],
           ppv = yn[["ppv"]], npv = yn[["npv"]], stage4_caught = if (any(s4)) mean(ok[s4]) else NA_real_,
           unsafe_rate = unsafe_rates(ref, ifelse(is.na(p), "", p))[["unsafe_rate"]])
  for (lv in JUDGE_LEVELS) out[[paste0("exact_", lv)]] <- if (any(level == lv)) mean(ok[level == lv]) else NA_real_
  out
}

judge_status_of <- function(judgments) {
  st <- judgments[judgments$kind == "status" & as.logical(judgments$gate_ok) & !is.na(judgments$judge_status), ]
  setNames(st$judge_status, st$visit_id)
}

judge_metrics_point <- function(answers, judgments, truth) {
  js <- judge_status_of(judgments)
  judged <- intersect(names(truth), names(js))
  rows <- list()
  for (s in unique(answers$system)) {
    a <- answers[answers$system == s, ]
    p <- setNames(a$answer, a$visit_id); lev <- setNames(a$difficulty, a$visit_id)
    ids <- names(truth)
    t_all <- judge_point(truth[ids], p[ids], lev[ids])
    t_j <- judge_point(truth[judged], p[judged], lev[judged])
    j <- judge_point(js[judged], p[judged], lev[judged])
    rows[[s]] <- data.frame(system = s, metric = JUDGE_METRICS, vs_truth = t_all[JUDGE_METRICS],
                            vs_truth_judged = t_j[JUDGE_METRICS], vs_judge = j[JUDGE_METRICS],
                            difference = j[JUDGE_METRICS] - t_j[JUDGE_METRICS], n_judged = length(judged))
  }
  out <- do.call(rbind, rows); rownames(out) <- NULL; out
}

judge_agreement_point <- function(judgments, truth, level) {
  js <- judge_status_of(judgments)[names(truth)]
  names(js) <- names(truth)
  groups <- c(list(list("all", "all", rep(TRUE, length(truth)))),
              lapply(sort(unique(truth)), function(v) list("truth_status", v, truth == v)),
              lapply(JUDGE_LEVELS, function(v) list("difficulty", v, level == v)))
  do.call(rbind, lapply(groups, function(g) {
    m <- g[[3]]; t <- truth[m]; j <- js[m]; has <- !is.na(j)
    data.frame(group = g[[1]], value = g[[2]], n = sum(m), coverage = mean(has),
               agreement = if (any(has)) mean(j[has] == t[has]) else NA_real_,
               kappa = if (any(has)) cohen_kappa(t[has], j[has]) else NA_real_)
  }))
}

read_judge_inputs <- function(prefix = "") {
  dir <- "data/datasets/judge/"
  na <- c("", "NA")
  answers <- read.csv(paste0(dir, prefix, "chart_answers.csv"), stringsAsFactors = FALSE, na.strings = na)
  judgments <- read.csv(paste0(dir, prefix, "judgments.csv"), stringsAsFactors = FALSE, na.strings = na)
  key <- read.csv("data/datasets/answer_key/review_key.csv", stringsAsFactors = FALSE)
  key <- key[key$visit_id %in% answers$visit_id, ]
  list(answers = answers, judgments = judgments,
       truth = setNames(key$truth_status, key$visit_id), level = setNames(key$difficulty, key$visit_id))
}

if (sys.nframe() == 0) {
  args <- commandArgs(trailingOnly = TRUE)
  inp <- read_judge_inputs(if (length(args) && args[1] == "simulated") "simulated_" else "")
  m <- judge_metrics_point(inp$answers, inp$judgments, inp$truth)
  print(head(m[m$metric == "exact_status", ], 10))
  print(judge_agreement_point(inp$judgments, inp$truth, inp$level))
}
