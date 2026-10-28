# Encoder rungs from R.
#
# Two ways, pick per question:
#
#  A. Frozen embeddings (default, pure R workflow). text::textEmbed() pulls the
#     model from Hugging Face and returns one vector per note; a penalised
#     multinomial regression on those vectors is the classifier. No GPU, fast
#     to iterate, and answers "how much does the encoder's pretraining know
#     about dental text?" It is NOT the same as fine-tuning, so its numbers are
#     reported under model_id "<id>+frozen" and are not compared head-to-head
#     with the Python fine-tuned rungs.
#
#  B. Fine-tuned (same numbers as Python). reticulate calls the Python
#     HFEncoder in python/health_transformation_lab_nlp/rungs.py, so the R user drives it and
#     the result is identical to the Python rung. Use this when the R and
#     Python leaderboards must line up.
#
# UNTESTED in CI: needs text::textrpp_install() (torch + transformers).

rung_encoder_frozen <- function(train, test, hf_id, max_len = 256) {
  embed <- function(x) {
    e <- text::textEmbed(x, model = hf_id, layers = -2,
                         aggregation_from_tokens_to_texts = "mean",
                         max_token_to_sentence = max_len)
    as.data.frame(e$texts[[1]])          # one row per note, one column per dimension
  }
  tr <- cbind(label = factor(train$label, levels = PERIO_LABELS), embed(train$note_text))
  te <- embed(test$note_text)
  fit <- workflow(recipe(label ~ ., data = tr) |> step_normalize(all_predictors()),
                  multinom_reg(penalty = 0.01, mixture = 0) |> set_engine("glmnet")) |> fit(tr)
  proba <- .proba_matrix(fit, te)
  list(pred = PERIO_LABELS[max.col(proba, ties.method = "first")], proba = proba)
}

rung_encoder_finetune <- function(train, test, rung_id, epochs = 3, max_len = 256) {
  sys <- reticulate::import("sys")
  sys$path$insert(0L, file.path(getwd(), "python"))
  registry <- reticulate::import("health_transformation_lab_nlp.registry")
  rungs <- reticulate::import("health_transformation_lab_nlp.rungs")
  model <- rungs$make_rung(rung_id, registry$load_registry(),
                           epochs = as.integer(epochs), max_len = as.integer(max_len))
  model$fit(reticulate::r_to_py(train))
  out <- model$predict(reticulate::r_to_py(test))
  proba <- reticulate::py_to_r(out[[2]]); colnames(proba) <- PERIO_LABELS
  list(pred = unlist(out[[1]]), proba = proba)
}
