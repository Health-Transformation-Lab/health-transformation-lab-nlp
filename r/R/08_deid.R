# De-identification cost-effectiveness (spec 007): R twin of python/health_transformation_lab_nlp/deid_eval.py
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

# ---- Review flows (spec 008): R twin of deid_review.agreement and deid_review.wilson / qa_summary.
# Reads data/deid/review/[simulated_]gold_spans.csv and qa_labels.csv from 31_deid_review_import.py.

# Pairwise entity F1 on the notes both annotators did: exact (start, end), then also same category.
# Rows with start = -1 are annotations with no spans (they count the note, not a span).
deid_agreement <- function(spans) {
  who <- sort(unique(spans$annotator))
  if (length(who) < 2) return(data.frame())
  out <- list()
  for (i in seq_len(length(who) - 1)) for (j in (i + 1):length(who)) {
    a <- who[i]; b <- who[j]
    notes <- intersect(spans$note_id[spans$annotator == a], spans$note_id[spans$annotator == b])
    m <- spans[spans$note_id %in% notes & spans$start >= 0, ]
    sa <- m[m$annotator == a, ]; sb <- m[m$annotator == b, ]
    k <- function(d, typed) unique(paste(d$note_id, d$start, d$end, if (typed) d$type else "", sep = "|"))
    n <- nrow(sa) + nrow(sb)
    f <- function(typed) if (n) 2 * length(intersect(k(sa, typed), k(sb, typed))) / n else NA_real_
    out[[length(out) + 1]] <- data.frame(annotator_a = a, annotator_b = b, n_notes = length(notes),
                                         f1_span = f(FALSE), f1_typed = f(TRUE), stringsAsFactors = FALSE)
  }
  do.call(rbind, out)
}

deid_wilson <- function(k, n, z = 1.959964) {
  if (n == 0) return(c(p = NA, lo = NA, hi = NA))
  p <- k / n
  centre <- (p + z^2 / (2 * n)) / (1 + z^2 / n)
  half <- z * sqrt(p * (1 - p) / n + z^2 / (4 * n^2)) / (1 + z^2 / n)
  c(p = p, lo = max(0, centre - half), hi = min(1, centre + half))
}

# Leak-note rate (Wilson CI) and over-redaction rate, pooled (any reviewer) and per reviewer.
deid_qa_summary <- function(labels) {
  labels$flag <- labels$leak == "yes"; labels$over <- labels$over_redaction == "yes"
  pooled <- data.frame(note_id = unique(labels$note_id))
  pooled$flag <- tapply(labels$flag, labels$note_id, any)[as.character(pooled$note_id)]
  pooled$over <- tapply(labels$over, labels$note_id, any)[as.character(pooled$note_id)]
  one <- function(scope, g) {
    w <- deid_wilson(sum(g$flag), nrow(g))
    data.frame(scope = scope, n_notes = nrow(g), leak_notes = sum(g$flag), leak_rate = w[["p"]],
               leak_lo = w[["lo"]], leak_hi = w[["hi"]], over_redaction_rate = mean(g$over), stringsAsFactors = FALSE)
  }
  rbind(one("pooled", pooled), do.call(rbind, lapply(sort(unique(labels$reviewer)),
                                                     function(r) one(r, labels[labels$reviewer == r, ]))))
}

deid_parse_spans <- function(s) {
  if (!length(s) || is.na(s) || !nzchar(s)) return(matrix(integer(), 0, 2))
  do.call(rbind, lapply(strsplit(strsplit(s, ";", fixed = TRUE)[[1]], "-", fixed = TRUE), as.integer))
}

deid_runs <- function(chars) {
  chars <- sort(unique(chars))
  if (!length(chars)) return(matrix(integer(), 0, 2))
  brk <- c(TRUE, diff(chars) != 1)
  starts <- chars[brk]; ends <- c(chars[which(brk)[-1] - 1], chars[length(chars)]) + 1
  cbind(starts, ends)
}

span_chars <- function(d) if (nrow(d)) unlist(mapply(function(a, b) seq.int(a, b - 1), d$start, d$end, SIMPLIFY = FALSE)) else integer()

# Consensus: characters marked by at least half the note's annotators (one vote per annotator);
# each run takes the most common category among the spans covering it (ties: alphabetical).
deid_consensus <- function(spans) {
  out <- list()
  for (nid in unique(spans$note_id)) {
    g <- spans[spans$note_id == nid, ]
    k <- length(unique(g$annotator))
    m <- g[g$start >= 0, ]
    votes <- table(unlist(lapply(split(m, m$annotator), function(ga) unique(span_chars(ga)))))
    keep <- as.integer(names(votes)[votes >= k / 2])
    r <- deid_runs(keep)
    for (i in seq_len(nrow(r))) {
      cov <- m[m$start < r[i, 2] & m$end > r[i, 1], ]
      tb <- table(cov$type)
      top <- sort(names(tb)[tb == max(tb)], method = "radix")[1]   # C order, as Python
      out[[length(out) + 1]] <- data.frame(note_id = nid, start = r[i, 1], end = r[i, 2], type = top,
                                           stringsAsFactors = FALSE)
    }
  }
  if (length(out)) do.call(rbind, out) else data.frame(note_id = integer(), start = integer(), end = integer(), type = character())
}

# Share of the generator's identifiers each annotator fully marked, aided vs unaided.
deid_annotator_recall <- function(spans, gen) {
  keys <- unique(spans[, c("annotator", "aided")])
  do.call(rbind, lapply(seq_len(nrow(keys)), function(i) {
    g <- spans[spans$annotator == keys$annotator[i] & spans$aided == keys$aided[i], ]
    found <- 0; total <- 0
    for (nid in unique(g$note_id)) {
      marked <- span_chars(g[g$note_id == nid & g$start >= 0, ])
      ph <- gen[gen$note_id == nid, ]
      total <- total + nrow(ph)
      found <- found + sum(vapply(seq_len(nrow(ph)), function(j) all(seq.int(ph$start[j], ph$end[j] - 1) %in% marked), logical(1)))
    }
    data.frame(annotator = keys$annotator[i], aided = keys$aided[i], n_notes = length(unique(g$note_id)),
               n_phi = total, entity_recall = if (total) found / total else NA_real_, stringsAsFactors = FALSE)
  }))
}

# Sensitivity, specificity and leak_span_recall against the answer key (qa_key.csv), per scope.
deid_qa_vs_key <- function(labels, key) {
  labels$leak_spans[is.na(labels$leak_spans)] <- ""; key$leak_spans[is.na(key$leak_spans)] <- ""
  labels$flag <- labels$leak == "yes"
  notes <- unique(labels$note_id)
  pooled <- data.frame(note_id = notes, flag = as.vector(tapply(labels$flag, labels$note_id, any)[as.character(notes)]),
                       leak_spans = vapply(notes, function(n) paste(labels$leak_spans[labels$note_id == n & nzchar(labels$leak_spans)],
                                                                    collapse = ";"), character(1)), stringsAsFactors = FALSE)
  truth <- setNames(key$n_true_leaks > 0, key$note_id)
  one <- function(scope, g) {
    t <- truth[as.character(g$note_id)]
    hit <- 0; tot <- 0
    for (i in seq_len(nrow(g))) {
      mk <- deid_parse_spans(g$leak_spans[i])
      lk <- deid_parse_spans(key$leak_spans[key$note_id == g$note_id[i]])
      for (j in seq_len(nrow(lk))) {
        tot <- tot + 1
        hit <- hit + any(mk[, 1] < lk[j, 2] & mk[, 2] > lk[j, 1])
      }
    }
    data.frame(scope = scope, sensitivity = if (any(t)) mean(g$flag[t]) else NA_real_,
               specificity = if (any(!t)) mean(!g$flag[!t]) else NA_real_,
               leak_span_recall = if (tot) hit / tot else NA_real_, stringsAsFactors = FALSE)
  }
  rbind(one("pooled", pooled), do.call(rbind, lapply(sort(unique(labels$reviewer)),
                                                     function(r) one(r, labels[labels$reviewer == r, ]))))
}
