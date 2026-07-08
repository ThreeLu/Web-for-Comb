import match as M


def test_word_boundary_rejects_substrings():
    pat = M.compile_keyword("oriented")
    assert pat.search("an oriented graph")
    assert not pat.search("the orientation of G")
    assert not pat.search("reoriented edges")


def test_optional_plural():
    pat = M.compile_keyword("Cayley graph")
    assert pat.search("a Cayley graph")
    assert pat.search("many Cayley graphs")


def test_hyphenated_keyword():
    pat = M.compile_keyword("Ramsey-Turán")
    assert pat.search("the Ramsey-Turán problem")
    assert not pat.search("Ramsey and Turán separately")


def test_case_insensitive():
    pat = M.compile_keyword("Hamilton cycle")
    assert pat.search("HAMILTON CYCLE decompositions")


def test_find_matches_records_reasons():
    p = {"title": "On oriented Cayley graphs", "summary": "", "authors": ["Noga Alon"]}
    kp = [(k, M.compile_keyword(k)) for k in ["oriented", "Cayley graph", "Hamilton cycle"]]
    r = M.find_matches(p, kp, ["Noga Alon", "Benny Sudakov"])
    assert set(r["keywords"]) == {"oriented", "Cayley graph"}
    assert r["authors"] == ["Noga Alon"]


def test_no_match_returns_empty():
    p = {"title": "A paper about nothing", "summary": "topology", "authors": ["X Y"]}
    kp = [(k, M.compile_keyword(k)) for k in ["Hamilton cycle"]]
    r = M.find_matches(p, kp, ["Noga Alon"])
    assert r == {"keywords": [], "authors": []}
