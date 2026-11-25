"""Offline tests for scripts/verify_citations.py (repo citations and the --corpus mode for papers)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("vc", Path(__file__).resolve().parent.parent / "scripts" / "verify_citations.py")
vc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vc)


def test_repo_citation_verified_and_missing(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("line one\nthe quick brown fox jumps\nline three\n")
    ok = vc.check_line(f'see {f}:2 "quick brown fox jumps"', tmp_path / "r.md")
    bad = vc.check_line(f'see {f}:2 "a sentence that is absent"', tmp_path / "r.md")
    assert ok[0][3] == "verified"
    assert bad[0][3] == "quote missing"


def test_corpus_normalizes_pdf_text(tmp_path):
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "paper.txt").write_text("we assume that all traded options are facili-\ntated by delta-hedgers; "
                                              "the coeﬃcient is −123.04")
    corpus = vc.load_corpus(tmp_path)
    hit = vc.check_corpus('S4 says "all traded options are facilitated by delta-hedgers" here', corpus)
    lig = vc.check_corpus('and "the coefficient is -123.04" too', corpus)
    miss = vc.check_corpus('but "dealers are observed directly" is not there', corpus)
    assert hit[0][0] == "in corpus" and hit[0][1].endswith("paper.txt")
    assert lig[0][0] == "in corpus"
    assert miss[0][0] == "not in corpus"


def test_corpus_skips_lines_with_repo_citations(tmp_path):
    assert vc.check_corpus('docs/x.md:3 "some quoted words here"', {}) == []
