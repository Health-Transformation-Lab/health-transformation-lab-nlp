"""Spec 010: a PHI tagger (Age, Sex, Date) on MACCROBAT's labels. Fixtures are invented sentences."""

from dental_omop_nlp import phi_tagger

TEXT = "An 8-year-old boy was seen on 12/18/2014. Fever began 3 days later."
ENTS = [{"start": 3, "end": 13, "type": "Age"}, {"start": 14, "end": 17, "type": "Sex"},
        {"start": 30, "end": 40, "type": "Date"}, {"start": 42, "end": 47, "type": "Sign_symptom"},
        {"start": 54, "end": 66, "type": "Date"}]
REC = {"note_id": "1", "text": TEXT, "entities": ENTS}


# ---------------------------------------------------------------- US1 BIO data
def test_words_split_hyphens_and_keep_offsets():
    ws = phi_tagger.words("An 8-year-old boy.")
    assert [w for w, _, _ in ws] == ["An", "8", "-", "year", "-", "old", "boy", "."]
    for w, a, b in ws:
        assert "An 8-year-old boy."[a:b] == w


def test_bio_docs_tag_only_age_sex_date():
    [d] = phi_tagger.bio_docs([REC])
    tagged = [(w, t) for w, t in zip(d["words"], d["tags"]) if t != "O"]
    assert tagged == [("8", "B-Age"), ("-", "I-Age"), ("year", "I-Age"), ("-", "I-Age"), ("old", "I-Age"),
                      ("boy", "B-Sex"), ("12", "B-Date"), ("/", "I-Date"), ("18", "I-Date"), ("/", "I-Date"),
                      ("2014", "I-Date"), ("3", "B-Date"), ("days", "I-Date"), ("later", "I-Date")]
    assert "Fever" in d["words"] and d["tags"][d["words"].index("Fever")] == "O"


def test_split_is_seeded_and_80_20():
    ids = [str(i) for i in range(50)]
    train, test = phi_tagger.split_docs(ids, test_share=0.2, seed=3)
    assert (train, test) == phi_tagger.split_docs(ids, test_share=0.2, seed=3)
    assert len(test) == 10 and not set(train) & set(test) and set(train) | set(test) == set(ids)


def test_write_conll_has_docstart_and_one_word_per_line(tmp_path):
    p = tmp_path / "train.txt"
    phi_tagger.write_conll(phi_tagger.bio_docs([REC]), p)
    lines = p.read_text().splitlines()
    assert lines[0] == "-DOCSTART- O" and "8 B-Age" in lines and "boy B-Sex" in lines
    assert "" in lines                                   # a blank line between sentences


# ---------------------------------------------------------------- US3 scores
def test_entities_read_bio_leniently():
    assert phi_tagger.entities(["B-Age", "I-Age", "O", "I-Date", "I-Date", "B-Date"]) == [
        ("Age", 0, 2), ("Date", 3, 5), ("Date", 5, 6)]


def test_score_is_exact_span_per_type_and_support_weighted():
    gold = [["B-Age", "I-Age", "O", "B-Sex", "O", "B-Date", "I-Date"]]
    pred = [["B-Age", "I-Age", "O", "O", "O", "B-Date", "O"]]          # Sex missed, Date boundary wrong
    s = phi_tagger.score(gold, pred).set_index("type")
    assert s.loc["Age", "f1"] == 1.0 and s.loc["Sex", "recall"] == 0.0 and s.loc["Date", "precision"] == 0.0
    assert abs(s.loc["weighted", "f1"] - (1 * 1.0 + 1 * 0 + 1 * 0) / 3) < 1e-12
    assert s.loc["weighted", "support"] == 3


def test_error_kinds_name_missed_spurious_boundary_and_type():
    gold = [["B-Age", "I-Age", "O", "B-Sex", "O", "B-Date", "I-Date", "O", "B-Age"]]
    pred = [["B-Age", "I-Age", "B-Date", "O", "O", "B-Date", "O", "O", "B-Date"]]
    e = phi_tagger.error_kinds(gold, pred)
    assert e[("Sex", "missed")] == 1 and e[("Date", "spurious")] == 1
    assert e[("Date", "boundary")] == 1 and e[("Age", "wrong_type")] == 1


# ---------------------------------------------------------------- US4 regex dates
def test_regex_dates_tag_only_words_the_model_left_o():
    text = "Seen in January 2014 and on 3/4/15; stage 2/3."
    ws = phi_tagger.words(text)
    tags = ["O"] * len(ws)
    out = phi_tagger.regex_dates(text, ws, tags, ["month_year", "numeric"])
    got = [(w, t) for (w, _, _), t in zip(ws, out) if t != "O"]
    assert got == [("January", "B-Date"), ("2014", "I-Date"), ("3", "B-Date"), ("/", "I-Date"), ("4", "I-Date"),
                   ("/", "I-Date"), ("15", "I-Date")]
    model = list(tags)
    model[ws.index(("January", 8, 15))] = "B-Age"                          # the model's own label wins
    assert phi_tagger.regex_dates(text, ws, model, ["month_year"])[ws.index(("January", 8, 15))] == "B-Age"


def test_every_named_pattern_compiles_and_has_an_example():
    for name, (rx, example) in phi_tagger.DATE_PATTERNS.items():
        assert rx.search(example), name


# ---------------------------------------------------------------- US2 chunks and alignment
def test_chunks_pack_whole_sentences_up_to_a_word_limit():
    [d] = phi_tagger.bio_docs([REC])
    assert [d["words"][a:b][-1] for a, b in d["sents"]] == [".", "."]
    one = phi_tagger.chunks(d, max_words=100)
    assert one == [(0, len(d["words"]))]
    two = phi_tagger.chunks(d, max_words=16)
    assert two == list(d["sents"])
    for a, b in phi_tagger.chunks(d, max_words=5):                     # a long sentence is cut
        assert b - a <= 5


def test_align_labels_the_first_sub_token_only():
    label2id = {t: i for i, t in enumerate(phi_tagger.LABELS)}
    word_ids = [None, 0, 1, 1, 2, None]
    assert phi_tagger.align(word_ids, ["O", "B-Age", "I-Age"], label2id) == [
        -100, label2id["O"], label2id["B-Age"], -100, label2id["I-Age"], -100]
    assert phi_tagger.LABELS[0] == "O" and len(phi_tagger.LABELS) == 7


# ---------------------------------------------------------------- boundary rules and overlap scores
def test_trim_function_words_fixes_date_edges_and_drops_empty_dates():
    ws = ["The", "next", "day", ",", "Nine", "months", "after", "the", "operation", "and", "the", "end"]
    tags = ["B-Date", "I-Date", "I-Date", "O", "B-Date", "I-Date", "I-Date", "I-Date", "O", "O", "B-Date", "O"]
    out = phi_tagger.fix_dates(ws, tags, ["trim_function_words"])
    assert phi_tagger.entities(out) == [("Date", 1, 3), ("Date", 4, 7)]
    assert out[1] == "B-Date" and out[0] == "O" and out[10] == "O"
    assert phi_tagger.fix_dates(ws, ["B-Age"] + tags[1:], ["trim_function_words"])[0] == "B-Age"   # other types untouched


def test_overlap_score_counts_a_same_type_overlap_as_a_match():
    gold = [["B-Date", "I-Date", "I-Date", "O", "B-Sex"]]
    pred = [["O", "B-Date", "I-Date", "I-Date", "O"]]
    exact = phi_tagger.score(gold, pred).set_index("type")
    loose = phi_tagger.score(gold, pred, overlap=True).set_index("type")
    assert exact.loc["Date", "f1"] == 0.0 and loose.loc["Date", "f1"] == 1.0 and loose.loc["Sex", "recall"] == 0.0


# ---------------------------------------------------------------- review fixes
def test_three_way_split_is_disjoint_and_seeded():
    ids = [str(i) for i in range(200)]
    tr, va, te = phi_tagger.three_way_split(ids, test_share=0.2, n_val=20, seed=42)
    assert (len(tr), len(va), len(te)) == (140, 20, 40)
    assert not (set(tr) & set(va) or set(tr) & set(te) or set(va) & set(te))
    assert (tr, va, te) == phi_tagger.three_way_split(ids, test_share=0.2, n_val=20, seed=42)
    assert te == phi_tagger.split_docs(ids, 0.2, 42)[1]            # same test set as the 80:20 split


def test_word_tags_take_the_first_sub_token_and_refuse_truncation():
    labels = ["O", "B-Age", "I-Age", "B-Date", "I-Date", "B-Sex", "I-Sex"]
    ids = [None, 0, 1, 1, 2, None]
    best = [0, 0, 1, 5, 2, 0]
    assert phi_tagger.word_tags(ids, best, 3, labels) == ["O", "B-Age", "I-Age"]
    import pytest
    with pytest.raises(ValueError, match="truncated"):
        phi_tagger.word_tags([None, 0, 1, None], [0, 0, 1, 0], 3, labels)


def test_regex_dates_extend_a_model_date_with_inside_tags():
    text = "Seen in January 2014 ."
    ws = phi_tagger.words(text)
    tags = ["O", "O", "B-Date", "O", "O"]
    assert phi_tagger.regex_dates(text, ws, tags, ["month_year"]) == ["O", "O", "B-Date", "I-Date", "O"]


def test_a_line_break_ends_a_sentence():
    [d] = phi_tagger.bio_docs([{"note_id": "1", "text": "Fever\nCough began", "entities": []}])
    assert d["sents"] == [(0, 1), (1, 3)]


def test_overlap_score_matches_one_to_one_so_fragments_do_not_count_twice():
    gold = [["B-Date", "I-Date", "I-Date", "I-Date"]]
    pred = [["B-Date", "B-Date", "B-Date", "B-Date"]]
    s = phi_tagger.score(gold, pred, overlap=True).set_index("type")
    assert s.loc["Date", "recall"] == 1.0 and s.loc["Date", "precision"] == 0.25
