# Spec 005 twins of python/dental_omop_nlp/plausibility.py and prevalence.py.
# Base R. r/tests/test_parity.R checks they match Python.

PERIO_LABELS6 <- c("healthy", "gingivitis", "periodontitis_stage_1", "periodontitis_stage_2",
                   "periodontitis_stage_3", "periodontitis_stage_4")
PLAUS_FLAGS <- c("cal_drop", "rbl_drop", "teeth_regained", "perio_resolved", "stage_drop")

# visits: visit_id, person_id, visit_date, charted, max_cal_mm, rbl_pct, teeth_lost_perio, <status_col>
check_history <- function(visits, status_col = "status", cal_tol = 1.5, rbl_tol = 5) {
  v <- visits[order(visits$person_id, as.character(visits$visit_date), visits$visit_id), ]
  out <- data.frame(visit_id = v$visit_id, person_id = v$person_id)
  for (f in PLAUS_FLAGS) out[[f]] <- FALSE
  last <- NULL; best <- NA; pid <- NA
  charted <- as.logical(v$charted)
  for (i in seq_len(nrow(v))) {
    if (!identical(v$person_id[i], pid)) { pid <- v$person_id[i]; last <- NULL; best <- NA }
    if (isTRUE(charted[i]) && !is.na(v$max_cal_mm[i])) {
      if (!is.null(last)) {
        out$cal_drop[i] <- last[1] - v$max_cal_mm[i] > cal_tol
        out$rbl_drop[i] <- last[2] - v$rbl_pct[i] > rbl_tol
        out$teeth_regained[i] <- v$teeth_lost_perio[i] < last[3]
      }
      last <- c(v$max_cal_mm[i], v$rbl_pct[i], v$teeth_lost_perio[i])
    }
    s <- v[[status_col]][i]
    if (s %in% PERIO_LABELS6) {
      rank <- match(s, PERIO_LABELS6) - 1
      if (!is.na(best) && best >= 2) {
        out$perio_resolved[i] <- rank < 2
        out$stage_drop[i] <- rank < best
      }
      best <- if (is.na(best)) rank else max(best, rank)
    }
  }
  out$any_flag <- apply(out[PLAUS_FLAGS], 1, any)
  out
}

wilson_ci <- function(k, n, z = 1.959963984540054) {
  if (n == 0) return(c(NA_real_, NA_real_))
  p <- k / n; d <- 1 + z^2 / n
  c0 <- (p + z^2 / (2 * n)) / d
  h <- z * sqrt(p * (1 - p) / n + z^2 / (4 * n^2)) / d
  c(max(0, c0 - h), min(1, c0 + h))
}

prevalence_by <- function(visits, status_col, by = NULL) {
  known <- c(PERIO_LABELS6, "healthy_gingivitis")
  perio <- PERIO_LABELS6[3:6]; severe <- PERIO_LABELS6[5:6]
  v <- visits[order(visits$person_id, as.character(visits$visit_date)), ]
  k <- v[v[[status_col]] %in% known, ]
  last <- k[!duplicated(k$person_id, fromLast = TRUE), ]
  people <- v[!duplicated(v$person_id), ]
  groups <- if (is.null(by)) list(all = TRUE) else sort(unique(people[[by]]))
  rows <- lapply(groups, function(g) {
    ppl <- if (is.null(by)) people else people[people[[by]] == g, ]
    lk <- if (is.null(by)) last else last[last[[by]] == g, ]
    n <- nrow(lk); k1 <- sum(lk[[status_col]] %in% perio); k2 <- sum(lk[[status_col]] %in% severe)
    c1 <- wilson_ci(k1, n); c2 <- wilson_ci(k2, n)
    data.frame(group = if (is.null(by)) "all" else g, n_people = n, n_unknown = nrow(ppl) - n,
               periodontitis = if (n) k1 / n else NA, periodontitis_ci_low = c1[1], periodontitis_ci_high = c1[2],
               stage3_4 = if (n) k2 / n else NA, stage3_4_ci_low = c2[1], stage3_4_ci_high = c2[2])
  })
  out <- do.call(rbind, rows)
  if (!is.null(by)) names(out)[1] <- by
  out
}
