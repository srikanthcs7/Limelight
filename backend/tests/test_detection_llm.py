import app.llm as llm_mod
from app.pipeline.detection import Entity, detect, extract_with_llm

ENTITIES = [
    Entity(name="GetQuizSolve", aliases=["Get Quiz Solve"], is_tracked_brand=True),
    Entity(name="Coursology", aliases=[], is_tracked_brand=False),
]

ANSWER = "GetQuizSolve is great. Coursology and StudyFetch are alternatives."


def test_extract_canonicalises_and_tags(monkeypatch):
    monkeypatch.setattr(
        llm_mod,
        "complete_json",
        lambda s, u, model=None: {
            "mentions": [
                {"name": "the GetQuizSolve extension", "position": 1, "sentiment": "positive"},
                {"name": "Coursology", "position": 2, "sentiment": "neutral"},
                {"name": "StudyFetch", "position": 3, "sentiment": "neutral"},
            ]
        },
    )
    mentions = extract_with_llm(ANSWER, ENTITIES)
    by_name = {m.entity_name: m for m in mentions}

    # loose match canonicalises to the tracked brand
    assert by_name["GetQuizSolve"].is_tracked_brand is True
    assert by_name["GetQuizSolve"].position == 1
    assert by_name["GetQuizSolve"].sentiment == "positive"
    # tracked competitor
    assert by_name["Coursology"].entity_type == "competitor"
    assert by_name["Coursology"].is_tracked_brand is False
    # untracked brand discovered by the LLM is kept as an untracked competitor
    assert "StudyFetch" in by_name
    assert by_name["StudyFetch"].is_tracked_brand is False


def test_detect_falls_back_to_fuzzy_on_llm_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no network")

    monkeypatch.setattr(llm_mod, "complete_json", boom)
    mentions = detect(ANSWER, ENTITIES)
    names = {m.entity_name for m in mentions}
    # fuzzy still finds the tracked entities by substring
    assert "GetQuizSolve" in names and "Coursology" in names


def test_detect_empty_answer():
    assert detect("", ENTITIES) == []
