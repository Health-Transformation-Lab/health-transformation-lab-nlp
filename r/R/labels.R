# Periodontal status from a perio chart. R twin of python/dental_omop_nlp/labels.py.
# Same rules, same thresholds; r/tests/test_parity.R checks the two agree on
# every row of data/labels/labeled_notes.csv. See the Python docstring for the
# clinical basis (2017 AAP/EFP, severity axis only).

PERIO_LABELS <- c("healthy", "gingivitis", "periodontitis_stage_1",
                  "periodontitis_stage_2", "periodontitis_stage_3", "periodontitis_stage_4")

label_chart <- function(max_probing_depth_mm, bop_pct, max_cal_mm, rbl_pct, teeth_lost_perio = 0) {
  # Vectorised over equal-length inputs.
  n <- length(bop_pct)
  teeth_lost_perio <- ifelse(is.na(teeth_lost_perio), 0, teeth_lost_perio)
  stopifnot(all(bop_pct >= 0 & bop_pct <= 100), all(rbl_pct >= 0 & rbl_pct <= 100))

  out <- character(n)
  no_loss <- max_cal_mm < 1 & rbl_pct < 15 & teeth_lost_perio == 0
  out[no_loss] <- ifelse(bop_pct[no_loss] >= 10, "gingivitis", "healthy")

  idx <- which(!no_loss)
  if (length(idx)) {
    cal <- max_cal_mm[idx]; rbl <- rbl_pct[idx]; lost <- teeth_lost_perio[idx]
    by_cal <- ifelse(cal <= 2, 1, ifelse(cal <= 4, 2, 3))
    by_rbl <- ifelse(rbl < 15, 1, ifelse(rbl <= 33, 2, 3))
    stage <- pmax(by_cal, by_rbl)
    stage[lost > 0 & stage < 3] <- 3
    stage[lost >= 5] <- 4
    out[idx] <- paste0("periodontitis_stage_", stage)
  }
  out
}

# ---- rules baseline: regex over the note text, then label_chart -------------
.num <- "(\\d+(?:\\.\\d+)?)"
.patterns <- list(
  pd   = c(paste0("PD max ", .num), paste0("probing depths up to ", .num), paste0("deepest pocket ", .num)),
  bop  = c(paste0("BOP ", .num, "%"), paste0("bleeding at ", .num, "%")),
  cal  = c(paste0("CAL ", .num), paste0("attachment loss ", .num)),
  rbl  = c(paste0("RBL ~?", .num, "%"), paste0(.num, "% horizontal bone loss")),
  lost = c(paste0(.num, " teeth previously lost"))
)

.find <- function(text, key) {
  for (p in .patterns[[key]]) {
    m <- regmatches(text, regexec(p, text, ignore.case = TRUE, perl = TRUE))[[1]]
    if (length(m) >= 2) return(as.numeric(m[2]))
  }
  NA_real_
}

rules_predict <- function(texts) {
  vapply(texts, function(t) {
    neg <- grepl("no BOP|BOP neg|no bleeding on probing", t, ignore.case = TRUE)
    z <- function(x) ifelse(is.na(x), 0, x)
    bop <- if (neg) 0 else z(.find(t, "bop"))
    label_chart(z(.find(t, "pd")), min(bop, 100), z(.find(t, "cal")),
                min(z(.find(t, "rbl")), 100), z(.find(t, "lost")))
  }, character(1), USE.NAMES = FALSE)
}

# Ladder interface (base R, no tidymodels needed).
rung_rules <- function(train, test) list(pred = rules_predict(test$note_text), proba = NULL)
