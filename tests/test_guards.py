import pytest
from src.cinemind.agents.guards import Guards, extract_evidence_quote
from src.cinemind.data.build_catalog import load_catalog
from src.cinemind.schemas import Candidate, Verdict, RankedOutputItem

def test_guard_drops_out_of_set_and_replaces():
    candidates = [
        Candidate(movie_id=1, title="Movie 1", overview="A nice movie about space. Exciting journey.", score=0.9),
        Candidate(movie_id=2, title="Movie 2", overview="A great thriller with twists and turns.", score=0.8),
        Candidate(movie_id=3, title="Movie 3", overview="A comedy story about dogs and cats.", score=0.7),
        Candidate(movie_id=4, title="Movie 4", overview="An adventure in mountains. High altitude.", score=0.6),
        Candidate(movie_id=5, title="Movie 5", overview="Historical drama about kings and queens.", score=0.5),
    ]
    verdicts = [
        Verdict(movie_id=1, match=True, fit=0.95, reason="Space adventure"),
        Verdict(movie_id=2, match=True, fit=0.90, reason="Thrilling plot"),
        Verdict(movie_id=3, match=True, fit=0.85, reason="Funny comedy"),
        Verdict(movie_id=4, match=True, fit=0.80, reason="Mountain adventure"),
        Verdict(movie_id=5, match=True, fit=0.75, reason="Period drama"),
    ]

    # Ranker attempts to output movie_id 999999 (NOT in candidates)
    model_rankings = [
        RankedOutputItem(movie_id=999999, reason="Hallucinated movie outside set"),
        RankedOutputItem(movie_id=1, reason="Great space adventure"),
        RankedOutputItem(movie_id=2, reason="Great thriller")
    ]

    result = Guards.apply_guards(
        rankings=model_rankings,
        candidates=candidates,
        verdicts=verdicts,
        k=5
    )

    # Acceptance criterion 1: 999999 is dropped and replaced; exactly 5 returned
    result_ids = [r.movie_id for r in result]
    assert 999999 not in result_ids
    assert len(result) == 5
    assert set(result_ids) == {1, 2, 3, 4, 5}

def test_guard_fills_short_lists_with_weak_matches():
    # Only 2 candidates judged match; 3 judged no match
    candidates = [
        Candidate(movie_id=i, title=f"M{i}", overview=f"Overview of movie {i}. Storyline unfolds.", score=0.5)
        for i in range(1, 6)
    ]
    verdicts = [
        Verdict(movie_id=1, match=True, fit=0.9, reason="Strong match 1"),
        Verdict(movie_id=2, match=True, fit=0.85, reason="Strong match 2"),
        Verdict(movie_id=3, match=False, fit=0.4, reason="Poor match 3"),
        Verdict(movie_id=4, match=False, fit=0.3, reason="Poor match 4"),
        Verdict(movie_id=5, match=False, fit=0.2, reason="Poor match 5"),
    ]

    model_rankings = [
        RankedOutputItem(movie_id=1, reason="Match 1"),
        RankedOutputItem(movie_id=2, reason="Match 2")
    ]

    result = Guards.apply_guards(
        rankings=model_rankings,
        candidates=candidates,
        verdicts=verdicts,
        k=5
    )

    # Acceptance criterion 3: Returns 5 items, remaining 3 labelled weak
    assert len(result) == 5
    weak_items = [r for r in result if r.is_weak_match]
    assert len(weak_items) == 3
    for w in weak_items:
        assert w.movie_id in {3, 4, 5}

def test_evidence_quote_is_exact_substring_across_catalog():
    # Acceptance criterion 2: Every attached quote is an exact substring of overview
    catalog = load_catalog()
    assert len(catalog) > 0

    sample_reasons = [
        "A compelling psychological thriller with twists and paranoia.",
        "An epic space journey through wormholes and time dilation.",
        "A heartwarming story of childhood friends, love, and destiny.",
        "A dark satirical comedy about social classes and deception.",
        "An intense action-packed survival story against all odds."
    ]

    for m in catalog:
        for reason in sample_reasons:
            quote = extract_evidence_quote(m.overview, reason)
            assert len(quote) > 0
            assert quote in m.overview, f"Quote '{quote}' not an exact substring in overview '{m.overview}'"
