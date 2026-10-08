from src.cinemind.data.build_catalog import build_catalog
from src.cinemind.eval.split import EvalSplitBuilder
from tests.movielens_fixture import write_fixture


def _build(tmp_path):
    raw = tmp_path / "raw"
    write_fixture(raw)
    cat = tmp_path / "processed" / "catalog.jsonl"
    build_catalog(output_path=cat, raw_dir=raw, download=False)
    return EvalSplitBuilder(seed=42, raw_dir=raw, catalog_path=cat)


def test_split_is_byte_identical_and_leak_free(tmp_path):
    builder = _build(tmp_path)
    p1, p2 = tmp_path / "s1.json", tmp_path / "s2.json"
    v1 = builder.build_split(num_viewers=15, output_file=p1)
    builder.build_split(num_viewers=15, output_file=p2)
    assert p1.read_bytes() == p2.read_bytes()

    assert len(v1) == 15
    for v in v1:
        train = {h["movie_id"] for h in v["train_history"]}
        assert len(v["train_history"]) >= 20
        assert v["ground_truth_ids"] and set(v["ground_truth_ids"]) <= {5, 6}
        assert not train & set(v["ground_truth_ids"])


def test_split_uses_only_real_positive_viewers(tmp_path):
    viewers = _build(tmp_path).build_split(num_viewers=1000)
    # users 1..40 rated movie 5; odd ones rated it 5.0, even ones 2.0; users 1..10 rated movie 6 at 4.0
    expected = {u for u in range(1, 41) if u % 2} | set(range(1, 11))
    assert {v["user_id"] for v in viewers} == expected
