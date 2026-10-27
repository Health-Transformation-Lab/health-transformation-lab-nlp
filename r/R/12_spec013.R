# Spec 013 twins: CAL reliability (python/dental_omop_nlp/reliability_cal.py). Base R.

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
