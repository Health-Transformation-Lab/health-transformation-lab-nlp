# Spec 013 twins: CAL reliability (python/health_transformation_lab_nlp/reliability_cal.py). Base R.

# Balanced nested ANOVA on CAL after an OLS time trend (d: patient_id, tooth, site, visit, years, cal_mm).
cal_nested_components <- function(d) {
  x <- d$years; y <- d$cal_mm
  slope <- if (var(x) > 0) sum((x - mean(x)) * (y - mean(y))) / sum((x - mean(x))^2) else 0
  r <- y - slope * x
  kt <- paste(d$patient_id, d$tooth); ks <- paste(kt, d$site)
  a <- length(unique(d$patient_id)); b <- length(unique(kt)) / a; c <- length(unique(ks)) / (a * b)
  n <- nrow(d) / (a * b * c)
  m_s <- ave(r, ks); m_t <- ave(r, kt); m_p <- ave(r, d$patient_id)
  ms_e <- sum((r - m_s)^2) / (a * b * c * (n - 1)); ms_s <- sum((m_s - m_t)^2) / (a * b * (c - 1))
  ms_t <- sum((m_t - m_p)^2) / (a * (b - 1)); ms_p <- sum((m_p - mean(r))^2) / (a - 1)
  list(slope_mm_per_year = slope, var_error = ms_e, var_site = max(0, (ms_s - ms_e) / n),
       var_tooth = max(0, (ms_t - ms_s) / (c * n)), var_patient = max(0, (ms_p - ms_t) / (b * c * n)))
}

cal_icc <- function(cm) {
  tot <- cm$var_patient + cm$var_tooth + cm$var_site + cm$var_error
  list(icc_patient = cm$var_patient / tot, icc_tooth = (cm$var_patient + cm$var_tooth) / tot,
       icc_site = (cm$var_patient + cm$var_tooth + cm$var_site) / tot, sem_mm = sqrt(cm$var_error))
}

stage_band_flips <- function(d) {
  ip <- d[d$site %in% c("MB", "DB", "ML", "DL"), ]
  w <- aggregate(cal_mm ~ patient_id + visit, data = ip, FUN = max)
  w <- w[order(w$patient_id, w$visit), ]
  w$band <- findInterval(w$cal_mm, c(1, 3, 5))
  prev <- ave(w$band, w$patient_id, FUN = function(z) c(NA, head(z, -1)))
  ok <- !is.na(prev)
  list(pairs = sum(ok), flip_rate = mean(w$band[ok] != prev[ok]), down_rate = mean(w$band[ok] < prev[ok]))
}

# ACES (python/health_transformation_lab_nlp/aces.py), one exam at a time. s: tooth, site, cal_mm, pd_mm, bop;
# t: tooth, present, missing_reason.
aces_non_adjacent <- function(teeth) {
  u <- sort(unique(teeth)); if (length(u) >= 3) return(TRUE); if (length(u) < 2) return(FALSE)
  !((u[1] <= 16) == (u[2] <= 16) && u[2] - u[1] == 1)
}
aces_exam <- function(s, t, case_cal = 1, bo_cal = 3, bo_pd = 3.5, complexity = TRUE,
                      stage4_rule = "opposing_pairs", bop_gingivitis = 10) {
  lg <- function(x) x == TRUE | x == "True" | x == "true"
  t$present <- lg(t$present); s$bop <- lg(s$bop)
  present_all <- t$tooth[t$present]
  pairs <- sum(sapply(2:15, function(k) (k %in% present_all) && ((33 - k) %in% present_all)))
  tt <- t[!(t$tooth %in% c(1, 16, 17, 32)), ]
  present <- tt$tooth[tt$present]
  if (!length(present)) return("edentulous")
  s <- s[s$tooth %in% present, ]
  ip <- s[s$site %in% c("MB", "DB", "ML", "DL") & !is.na(s$cal_mm), ]
  if (!aces_non_adjacent(ip$tooth)) return("non_classified")
  bo <- s[s$site %in% c("B", "L"), ]
  case <- aces_non_adjacent(ip$tooth[ip$cal_mm >= case_cal]) ||
    length(unique(bo$tooth[bo$cal_mm >= bo_cal & bo$pd_mm >= bo_pd])) >= 2
  if (!case) return(if (100 * mean(s$bop) >= bop_gingivitis) "gingivitis" else "healthy")
  m <- max(ip$cal_mm)
  if (m < 3) return("periodontitis_stage_1")
  if (m < 5) {
    deep <- s[s$pd_mm >= 6 & !(s$tooth %in% c(2, 15, 18, 31) & s$site %in% c("DB", "DL")), ]
    return(if (complexity && aces_non_adjacent(deep$tooth)) "periodontitis_stage_3" else "periodontitis_stage_2")
  }
  if (!complexity) return("periodontitis_stage_3_4")
  miss <- tt[!tt$present, ]
  four <- switch(stage4_rule, opposing_pairs = pairs < 10, teeth20 = length(present) < 20,
                 teeth_lost_perio = sum(miss$missing_reason == "perio") >= 5, all_missing_perio = nrow(miss) >= 5)
  if (four) "periodontitis_stage_4" else "periodontitis_stage_3"
}
