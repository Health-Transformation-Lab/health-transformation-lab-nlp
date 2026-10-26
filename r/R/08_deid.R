# De-identification cost-effectiveness (spec 007): R twin of python/dental_omop_nlp/deid_eval.py
# (engine_cost, review_cost, cost_table, deid_frontier). Reads data/deid/cost_inputs.csv,
# written by python/scripts/26_deid_benchmark.py; must reproduce cost_effectiveness.csv.
# Base R only.

deid_engine_cost <- function(kind, hardware, notes_per_sec, unit, usd_per_unit, free_units,
                             n_notes, avg_chars, cpu_usd_h, gpu_usd_h, llm = NULL) {
  if (kind == "local") {
    rate <- if (identical(hardware, "gpu")) gpu_usd_h else cpu_usd_h
    return(n_notes / notes_per_sec / 3600 * rate)
  }
  if (kind == "llm") return(n_notes * ((llm$prompt_overhead_tokens + avg_chars / 4) * llm$usd_per_1m_input_tokens +
                                       llm$output_tokens * llm$usd_per_1m_output_tokens) / 1e6)
  units <- if (unit == "mb") n_notes * avg_chars / 1e6 else n_notes * ceiling(avg_chars / 1000)
  max(units - free_units, 0) * usd_per_unit
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
                                    prompt_overhead_tokens = prompt_overhead_tokens, output_tokens = output_tokens))),
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
