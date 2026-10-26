# Spec 005 twins, R side: evidence-order search (phenotype.score_orders), data-quality checks
# (dq.run_checks) and next-visit progression (prediction.make_pairs + unpenalized logistic
# regression). Base R. r/tests/test_parity.R checks they match Python.
#
# Random parts are shared, not re-drawn: the select / holdout halves come from
# phenotype_orders_split.csv and the train / test people from test_predictions_<outcome>.csv,
# both written by the Python scripts. Bootstrap CIs and permutation importance use each
# language's own RNG, so they agree only approximately and aren't parity-tested.

source("r/R/04_reliability.R")
source("r/R/06_validation.R")

# ---------------------------------------------------------------- evidence order
DESIGN_GROUPS <- list(exam_form = "exam_form", dx_code = c("proc_dx_completed", "proc_dx_planned"),
                      notes = "notes", probing_chart = "probing_chart")
DESIGN_ORDER <- c("exam_form", "dx_code", "notes", "probing_chart")

permutations <- function(x) {
  if (length(x) <= 1) return(list(x))
  out <- list()
  for (i in seq_along(x)) for (p in permutations(x[-i])) out[[length(out) + 1]] <- c(x[i], p)
  out
}

# First evidence in priority order with an answer (no radiograph lower bound for order search).
phenotype_by_priority <- function(key, priority) {
  status <- rep("unknown", nrow(key)); done <- rep(FALSE, nrow(key))
  for (m in priority) {
    v <- key[[m]]; has <- !done & !is.na(v) & v != "" & v != "unknown"
    status[has] <- v[has]; done <- done | has
  }
  status
}

score_orders_r <- function(key, wide, split, five = TRUE) {
  f <- if (five) collapse5 else identity
  cats <- if (five) FIVE_ORDER else STATUS_ORDER
  ids <- sort(intersect(as.numeric(rownames(wide)), key$visit_id))
  k <- key[match(ids, key$visit_id), ]
  w <- wide[as.character(ids), , drop = FALSE]
  cons <- f(consensus(w)); names(cons) <- ids
  wf <- as.data.frame(lapply(w, f), stringsAsFactors = FALSE); rownames(wf) <- ids
  rows <- lapply(permutations(names(DESIGN_GROUPS)), function(order) {
    pred <- f(phenotype_by_priority(k, unlist(DESIGN_GROUPS[order]))); names(pred) <- ids
    out <- data.frame(order = paste(order, collapse = ">"), is_design_order = identical(order, DESIGN_ORDER))
    for (half in c("select", "holdout")) {
      h <- as.character(sort(split$visit_id[split$half == half]))
      p <- pred[h]; c0 <- cons[h]; ok <- c0 %in% cats & p %in% cats
      out[[paste0(half, "_n")]] <- sum(ok)
      out[[paste0(half, "_coverage")]] <- mean(p %in% cats)
      out[[paste0(half, "_pct_agree")]] <- if (any(ok)) mean(p[ok] == c0[ok]) else NA_real_
      out[[paste0(half, "_kappa")]] <- cohen_kappa(p[ok], c0[ok])
    }
    h <- as.character(sort(split$visit_id[split$half == "holdout"]))
    vh <- agreement_vs_humans(wf[h, , drop = FALSE], list(m = pred[h]), n_boot = 0)
    out$holdout_diff_vs_human_bar <- vh$diff_vs_human_bar[vh$kind == "method"]
    out
  })
  t <- do.call(rbind, rows)
  t <- t[order(-t$select_kappa), ]
  t$selected <- seq_len(nrow(t)) == 1
  t
}

# ---------------------------------------------------------------- data quality
DQ_RANGES <- list(probing_depth_range = c("rec_max_probing_depth_mm", 0, 15), cal_range = c("rec_max_cal_mm", 0, 15),
                  bop_range = c("rec_bop_pct", 0, 100), rbl_range = c("rec_rbl_pct", 0, 100),
                  teeth_lost_range = c("rec_teeth_lost_perio", 0, 32))
DQ_COMPLETENESS <- c("notes", "exam_form", "proc_dx_completed", "probing_chart")

dq_row <- function(check, category, n, fail, threshold = 0.05) {
  status <- if (is.null(threshold)) "REPORT" else if (n == 0 || fail / n <= threshold) "PASS" else "FAIL"
  data.frame(check = paste0(category, ":", check), category = category, n_checked = n, n_fail = fail,
             pass_rate = if (n) 1 - fail / n else NA_real_, status = status)
}

run_checks_r <- function(v, today) {
  out <- list()
  ch <- v[as.logical(v$charted), ]
  for (nm in names(DQ_RANGES)) {
    r <- DQ_RANGES[[nm]]; x <- ch[[r[1]]]; x <- x[!is.na(x)]
    out[[length(out) + 1]] <- dq_row(nm, "conformance", length(x), sum(x < as.numeric(r[2]) | x > as.numeric(r[3])))
  }
  d <- as.Date(substr(v$visit_date, 1, 10))
  out[[length(out) + 1]] <- dq_row("visit_not_future", "conformance", length(d), sum(d > as.Date(today)))
  for (c in DQ_COMPLETENESS) if (c %in% names(v))
    out[[length(out) + 1]] <- dq_row(c, "completeness", nrow(v), sum(v[[c]] == "unknown"), threshold = NULL)
  out[[length(out) + 1]] <- dq_row("age_range", "plausibility", nrow(v), sum(v$age < 18 | v$age > 110))
  hist <- v; names(hist)[match(c("rec_max_cal_mm", "rec_rbl_pct", "rec_teeth_lost_perio"), names(hist))] <-
    c("max_cal_mm", "rbl_pct", "teeth_lost_perio")
  f <- check_history(hist, status_col = "probing_chart")
  later <- f[f$visit_id %in% v$visit_id[duplicated(v$person_id)], ]
  for (fl in PLAUS_FLAGS) out[[length(out) + 1]] <- dq_row(paste0("temporal_", fl), "plausibility", nrow(later), sum(later[[fl]]))
  do.call(rbind, out)
}

# ---------------------------------------------------------------- progression
PRED_FEATURES <- c("age", "smoker_1_9", "smoker_10plus", "diabetes", "treated_before", "charted", "current_rank",
                   "max_probing_depth_mm", "bop_pct", "max_cal_mm", "rbl_pct", "teeth_lost_perio")
PRED_CHART <- c(rec_max_probing_depth_mm = "max_probing_depth_mm", rec_bop_pct = "bop_pct",
                rec_max_cal_mm = "max_cal_mm", rec_rbl_pct = "rbl_pct", rec_teeth_lost_perio = "teeth_lost_perio")
PRED_RANK <- c(setNames(0:5, STATUS_ORDER), healthy_gingivitis = 0)

make_pairs_r <- function(visits, status_col) {
  v <- visits[visits[[status_col]] %in% names(PRED_RANK), ]
  v <- v[order(v$person_id, as.character(v$visit_date), method = "radix"), ]
  nxt <- c(v[[status_col]][-1], NA); same <- c(v$person_id[-1] == v$person_id[-nrow(v)], FALSE)
  v$next_rank <- ifelse(same, PRED_RANK[nxt], NA)
  v <- v[!is.na(v$next_rank), ]
  v$current_rank <- unname(PRED_RANK[v[[status_col]]])
  v$y_progress <- as.integer(v$next_rank > v$current_rank)
  v$smoker_1_9 <- as.integer(v$cigarettes_per_day > 0 & v$cigarettes_per_day < 10)
  v$smoker_10plus <- as.integer(v$cigarettes_per_day >= 10)
  for (src in names(PRED_CHART)) {
    x <- as.numeric(v[[src]]); x[is.na(x)] <- if (any(!is.na(x))) stats::median(x, na.rm = TRUE) else 0
    v[[PRED_CHART[[src]]]] <- x
  }
  tf <- function(x) as.integer(as.logical(x) %in% TRUE)
  for (c in c("diabetes", "treated_before", "charted")) v[[c]] <- tf(v[[c]])
  v[, c("visit_id", "person_id", PRED_FEATURES, "y_progress")]
}

auroc <- function(y, p) {          # Mann-Whitney form; ties count half
  r <- rank(p); n1 <- sum(y == 1); n0 <- sum(y == 0)
  (sum(r[y == 1]) - n1 * (n1 + 1) / 2) / (n1 * n0)
}

fit_progression_r <- function(pairs, test_ids) {
  te <- pairs$visit_id %in% test_ids
  fit <- stats::glm(stats::reformulate(PRED_FEATURES, "y_progress"), data = pairs[!te, ], family = stats::binomial())
  p <- stats::predict(fit, newdata = pairs[te, ], type = "response")
  list(test = data.frame(visit_id = pairs$visit_id[te], p = unname(p)),
       auroc = auroc(pairs$y_progress[te], p), coef = stats::coef(fit))
}
