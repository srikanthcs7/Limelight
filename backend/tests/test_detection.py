from app.pipeline.detection import Entity, detect_mentions


def _entities():
    return [
        Entity(name="GetQuizSolve", aliases=["Get Quiz Solve"], is_tracked_brand=True),
        Entity(name="Coursology", aliases=[], is_tracked_brand=False),
        Entity(name="QuizAce", aliases=["Quiz Ace"], is_tracked_brand=False),
        Entity(name="CheatMate", aliases=[], is_tracked_brand=False),
        Entity(name="NotPresentCo", aliases=[], is_tracked_brand=False),
    ]


TEXT = (
    "For online courses, GetQuizSolve is a popular AI study helper. "
    "Coursology and QuizAce are alternatives, and CheatMate is also mentioned."
)


def test_positions_follow_appearance_order():
    mentions = detect_mentions(TEXT, _entities())
    by_name = {m.entity_name: m for m in mentions}
    assert by_name["GetQuizSolve"].position == 1
    assert by_name["Coursology"].position == 2
    assert by_name["QuizAce"].position == 3
    assert by_name["CheatMate"].position == 4


def test_absent_entity_not_returned():
    names = {m.entity_name for m in detect_mentions(TEXT, _entities())}
    assert "NotPresentCo" not in names


def test_tracked_brand_flagged_and_prominence_decays():
    mentions = detect_mentions(TEXT, _entities())
    brand = next(m for m in mentions if m.entity_name == "GetQuizSolve")
    assert brand.is_tracked_brand and brand.entity_type == "brand"
    assert brand.prominence == 1.0
    later = next(m for m in mentions if m.position == 2)
    assert later.prominence < brand.prominence


def test_alias_match():
    text = "I tried Get Quiz Solve last week."
    mentions = detect_mentions(text, _entities())
    assert any(m.entity_name == "GetQuizSolve" for m in mentions)
