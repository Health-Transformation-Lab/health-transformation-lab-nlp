# Spec 006: R twin of python/health_transformation_lab_nlp/sites.py derive() and cdc_aap().
# Base R. sites: visit_id, tooth, site, pd_mm, cal_mm, bop; teeth: visit_id, tooth,
# present, missing_reason, furcation_class, mobility_degree.

INTERPROXIMAL <- c("MB", "DB", "ML", "DL")

derive_sites <- function(sites, teeth) {
  lg <- function(x) x == TRUE | x == "True" | x == "true"
  sites$bop <- lg(sites$bop); teeth$present <- lg(teeth$present)
  ids <- sort(unique(teeth$visit_id))
  do.call(rbind, lapply(ids, function(id) {
    s <- sites[sites$visit_id == id, ]; t <- teeth[teeth$visit_id == id, ]
    ip <- s[s$site %in% INTERPROXIMAL, ]
    cal <- tapply(ip$cal_mm, ip$tooth, max); pdt <- tapply(ip$pd_mm, ip$tooth, max)
    p <- t[t$present, ]
    data.frame(visit_id = id, n_teeth_present = nrow(p),
               teeth_lost_perio = sum(t$missing_reason == "perio", na.rm = TRUE),
               max_probing_depth_mm = max(s$pd_mm), max_cal_mm = max(ip$cal_mm),
               bop_pct = 100 * mean(s$bop), pct_teeth_ip_cal1 = 100 * sum(cal >= 1) / nrow(p),
               n_teeth_ip_cal3 = sum(cal >= 3), n_teeth_ip_cal4 = sum(cal >= 4), n_teeth_ip_cal6 = sum(cal >= 6),
               n_teeth_ip_pd4 = sum(pdt >= 4), n_teeth_ip_pd5 = sum(pdt >= 5), n_sites_ip_pd5 = sum(ip$pd_mm >= 5),
               max_furcation_class = max(p$furcation_class), max_mobility_degree = max(p$mobility_degree))
  }))
}

cdc_aap <- function(d) {
  ifelse(d$n_teeth_ip_cal6 >= 2 & d$n_sites_ip_pd5 >= 1, "severe",
  ifelse(d$n_teeth_ip_cal4 >= 2 | d$n_teeth_ip_pd5 >= 2, "moderate",
  ifelse((d$n_teeth_ip_cal3 >= 2 & d$n_teeth_ip_pd4 >= 2) | d$n_sites_ip_pd5 >= 1, "mild", "none")))
}
