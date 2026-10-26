# De-identification cost-effectiveness (spec 007): R twin of python/dental_omop_nlp/deid_eval.py
# (engine_cost, review_cost, cost_table, deid_frontier). Reads data/deid/cost_inputs.csv,
# written by python/scripts/26_deid_benchmark.py; must reproduce cost_effectiveness.csv.
# Base R only.

# "1000000:0.0014;inf:0.00025" -> volume tiers (upper bound in units, USD per unit); "" -> none
deid_parse_tiers <- function(s) {
  if (is.null(s) || is.na(s) || !nzchar(s)) return(NULL)
  parts <- strsplit(strsplit(s, ";", fixed = TRUE)[[1]], ":", fixed = TRUE)
  data.frame(hi = vapply(parts, function(x) if (x[1] == "inf") Inf else as.numeric(x[1]), numeric(1)),
             usd = vapply(parts, function(x) as.numeric(x[2]), numeric(1)))
}

deid_engine_cost <- function(kind, hardware, notes_per_sec, unit, usd_per_unit, free_units,
                             n_notes, avg_chars, cpu_usd_h, gpu_usd_h, llm = NULL, tiers = "", lic = NULL) {
  if (kind == "local") {
    rate <- if (identical(hardware, "gpu")) gpu_usd_h else cpu_usd_h
    return(n_notes / notes_per_sec / 3600 * rate)
  }
  if (kind == "licensed") {                                          # licence + the node it runs on
    hours <- n_notes * avg_chars / lic$chars_per_sec / 3600
    pr <- lic$prorate_license; if (is.null(pr) || is.na(pr)) pr <- 0     # missing or NaN = whole months (as Python)
    months <- if (pr != 0) hours / lic$hours_per_month else ceiling(hours / lic$hours_per_month)
    return(hours * lic$node_usd_per_hour + months * lic$license_usd_per_month)
  }
  if (kind == "llm") {
    echo <- if (is.null(llm$output_echoes_note) || is.na(llm$output_echoes_note)) 0 else llm$output_echoes_note
    tout <- llm$output_tokens + if (echo != 0) avg_chars / 4 else 0     # e.g. ai_mask returns the whole note
    return(n_notes * ((llm$prompt_overhead_tokens + avg_chars / 4) * llm$usd_per_1m_input_tokens +
                      tout * llm$usd_per_1m_output_tokens) / 1e6)
  }
  units <- if (unit == "mb") n_notes * avg_chars / 1e6 else
    if (unit == "record_100_chars") n_notes * ceiling(avg_chars / 100) else n_notes * ceiling(avg_chars / 1000)
  units <- max(units - free_units, 0)
  tt <- deid_parse_tiers(tiers)
  if (is.null(tt)) return(units * usd_per_unit)
  lo <- c(0, head(tt$hi, -1))
  sum(pmax(pmin(units, tt$hi) - lo, 0) * tt$usd)
}

deid_frontier <- function(t) {
  if (is.null(t$decoy_damage)) t$decoy_damage <- 0
  t <- t[order(t$cost_usd, t$leaked_per_1m_notes, t$decoy_damage, t$method, method = "radix"), ]
  t$dominated <- FALSE; best <- Inf
  for (i in seq_len(nrow(t))) {
    if (t$leaked_per_1m_notes[i] >= best) t$dominated[i] <- TRUE else best <- t$leaked_per_1m_notes[i]
  }
  t$icer_usd_per_leak_avoided <- NA_real_; t$compared_to <- ""
  prev <- NA
  for (i in which(!t$dominated)) {
    if (!is.na(prev)) {
      t$icer_usd_per_leak_avoided[i] <- (t$cost_usd[i] - t$cost_usd[prev]) /
        (t$leaked_per_1m_notes[prev] - t$leaked_per_1m_notes[i])
      t$compared_to[i] <- t$method[prev]
    }
    prev <- i
  }
  t$usd_per_1k_leaks_avoided <- t$icer_usd_per_leak_avoided * 1000
  t
}

deid_cost_table <- function(ci) {
  one_tier <- function(g) {
    rows <- lapply(split(g, factor(g$method, levels = unique(g$method))), function(m) {
      eng <- sum(vapply(seq_len(nrow(m)), function(i) with(m[i, ],
        deid_engine_cost(kind, ifelse(is.na(hardware) | hardware == "", "cpu", hardware), notes_per_sec,
                         unit, usd_per_unit, free_units, n_notes, avg_chars,
                         cpu_node_usd_per_hour, gpu_node_usd_per_hour,
                         llm = list(usd_per_1m_input_tokens = usd_per_1m_input_tokens,
                                    usd_per_1m_output_tokens = usd_per_1m_output_tokens,
                                    prompt_overhead_tokens = prompt_overhead_tokens, output_tokens = output_tokens,
                                    output_echoes_note = if (exists("output_echoes_note")) output_echoes_note else 0),
                         tiers = if (exists("tiers")) tiers else "",
                         lic = if (exists("license_usd_per_month"))
                           list(chars_per_sec = chars_per_sec, node_usd_per_hour = node_usd_per_hour,
                                license_usd_per_month = license_usd_per_month, hours_per_month = hours_per_month,
                                prorate_license = prorate_license) else NULL)),
        numeric(1)))
      r0 <- m[1, ]
      rev <- r0$qa_sample_share * r0$n_notes * r0$minutes_per_note / 60 * r0$review_usd_per_hour
      data.frame(method = r0$method, engine_usd = eng, review_usd = rev, cost_usd = eng + rev,
                 leaked_per_1m_notes = r0$leaked_per_1m_notes, decoy_damage = r0$decoy_damage,
                 tier = r0$tier, stringsAsFactors = FALSE)
    })
    deid_frontier(do.call(rbind, rows))
  }
  do.call(rbind, lapply(split(ci, factor(ci$tier, levels = unique(ci$tier))), one_tier))
}
