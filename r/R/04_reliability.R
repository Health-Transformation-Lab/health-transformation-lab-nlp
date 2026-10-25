# Quantitative validation in R: reviewer reliability, and every method /
# the rule-based algorithm / each AI model against the reviewers.
# Twin of python/dental_omop_nlp/reliability.py; r/tests/test_parity.R checks they agree.
# Base R only. The `irr` package (kappam.fleiss, kappa2) gives the same
# Fleiss and Cohen numbers if you prefer it; see the cross-check at the bottom.
#
#   Rscript r/R/04_reliability.R             # real reviewers: data/review/reviewer_labels.csv
#   Rscript r/R/04_reliability.R simulated   # dry run: simulated_reviewer_labels.csv

STATUS_ORDER <- c("healthy", "gingivitis", "periodontitis_stage_1",
                  "periodontitis_stage_2", "periodontitis_stage_3", "periodontitis_stage_4")

cohen_kappa <- function(a, b) {
  n <- length(a); if (!n) return(NA_real_)
  cats <- union(a, b)
  po <- mean(a == b)
  pe <- sum(vapply(cats, function(c) mean(a == c) * mean(b == c), numeric(1)))
  if (pe == 1) NA_real_ else (po - pe) / (1 - pe)
}

weighted_kappa <- function(a, b, order = STATUS_ORDER) {
  keep <- a %in% order & b %in% order
  x <- match(a[keep], order); y <- match(b[keep], order); k <- length(order)
  if (!length(x)) return(NA_real_)
  O <- table(factor(x, 1:k), factor(y, 1:k)); O <- matrix(O, k, k)
  W <- outer(1:k, 1:k, function(i, j) (i - j)^2 / (k - 1)^2)
  E <- outer(rowSums(O), colSums(O)) / sum(O)
  1 - sum(W * O) / sum(W * E)
}

fleiss_kappa <- function(wide) {
  w <- wide[stats::complete.cases(wide), , drop = FALSE]
  m <- as.matrix(w); n <- ncol(m)
  cats <- sort(unique(as.vector(m)))
  counts <- sapply(cats, function(c) rowSums(m == c))
  if (is.null(dim(counts))) counts <- matrix(counts, nrow = nrow(m))
  p_j <- colSums(counts) / sum(counts)
  P_i <- rowSums(counts * (counts - 1)) / (n * (n - 1))
  (mean(P_i) - sum(p_j^2)) / (1 - sum(p_j^2))
}

consensus <- function(wide) {
  apply(wide, 1, function(r) {
    r <- r[!is.na(r)]; if (!length(r)) return("no_consensus")
    tab <- sort(table(r), decreasing = TRUE)
    if (length(tab) > 1 && tab[[1]] == tab[[2]]) "no_consensus" else names(tab)[1]
  })
}

reliability_report <- function(labels, key, compare) {
  wide <- reshape(labels[, c("visit_id", "reviewer", "status")], idvar = "visit_id",
                  timevar = "reviewer", direction = "wide")
  rownames(wide) <- wide$visit_id; wide$visit_id <- NULL
  names(wide) <- sub("^status\\.", "", names(wide))
  wide <- wide[order(as.numeric(rownames(wide))), , drop = FALSE]
  ids <- rownames(wide)
  cons <- consensus(wide)
  both_k <- function(a, b) { ok <- a %in% STATUS_ORDER & b %in% STATUS_ORDER; cohen_kappa(a[ok], b[ok]) }

  methods <- c(list(generator_chart_truth = setNames(key$truth_status, key$visit_id)), compare)
  rows <- lapply(names(methods), function(nm) {
    s <- unname(methods[[nm]][ids]); has <- s %in% STATUS_ORDER
    ok <- cons %in% STATUS_ORDER & has
    data.frame(method = nm, coverage = mean(has), n = sum(ok),
               pct_agree_consensus = mean(s[ok] == cons[ok]),
               kappa_vs_consensus = cohen_kappa(s[ok], cons[ok]),
               weighted_kappa_vs_consensus = weighted_kappa(s[ok], cons[ok]),
               mean_kappa_vs_each_reviewer = mean(sapply(names(wide), function(r) both_k(s, wide[[r]])), na.rm = TRUE))
  })
  list(n_visits = nrow(wide), n_reviewers = ncol(wide), fleiss_kappa = fleiss_kappa(wide),
       consensus_reached = mean(cons %in% STATUS_ORDER), methods = do.call(rbind, rows),
       consensus = data.frame(visit_id = as.integer(ids), consensus = cons))
}

if (sys.nframe() == 0) {
  sim <- identical(commandArgs(trailingOnly = TRUE)[1], "simulated")
  prefix <- if (sim) "simulated_" else ""
  labels <- read.csv(file.path("data/review", paste0(prefix, "reviewer_labels.csv")), stringsAsFactors = FALSE)
  key <- read.csv("data/datasets/answer_key/review_key.csv", stringsAsFactors = FALSE)
  m <- c("notes", "exam_form", "proc_codes_completed", "proc_codes_planned",
         "proc_dx_completed", "proc_dx_planned", "probing_chart", "algorithm_v0")
  compare <- setNames(lapply(m, function(x) setNames(key[[x]], key$visit_id)), m)
  for (f in sort(Sys.glob("data/datasets/ai_predictions_*.csv"))) {
    p <- read.csv(f, stringsAsFactors = FALSE)
    compare[[paste0("ai:", sub("^ai_predictions_(.*)\\.csv$", "\\1", basename(f)))]] <- setNames(p$pred, p$visit_id)
  }
  rep <- reliability_report(labels, key, compare)
  out <- file.path("data/review", paste0(prefix, "reliability"))
  dir.create(out, recursive = TRUE, showWarnings = FALSE)
  write.csv(rep$methods, file.path(out, "methods_vs_reviewers_R.csv"), row.names = FALSE)
  if (sim) cat("*** SIMULATED REVIEWERS: pipeline dry run, not a result ***\n")
  cat(sprintf("charts=%d reviewers=%d Fleiss kappa=%.3f consensus reached=%.1f%%\n",
              rep$n_visits, rep$n_reviewers, rep$fleiss_kappa, 100 * rep$consensus_reached))
  print(rep$methods, digits = 3, row.names = FALSE)

  if (requireNamespace("irr", quietly = TRUE)) {   # optional cross-check
    w <- reshape(labels[, c("visit_id", "reviewer", "status")], idvar = "visit_id", timevar = "reviewer", direction = "wide")
    cat("irr::kappam.fleiss:", round(irr::kappam.fleiss(w[stats::complete.cases(w), -1])$value, 3), "\n")
  }
}
