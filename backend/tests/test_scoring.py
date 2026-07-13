from app.pipeline.scoring import W_CITATION, W_MENTION, W_SOV, composite_score


def test_composite_perfect_visibility():
    # Always mentioned, first position, sole voice, always cited -> 100.
    assert composite_score(1.0, 1.0, 1.0, 1.0) == 100.0


def test_composite_zero():
    assert composite_score(0.0, 0.0, 0.0, 0.0) == 0.0


def test_weights_sum_to_one():
    assert round(W_MENTION + W_SOV + W_CITATION, 6) == 1.0


def test_prominence_scales_mention_component():
    # Half prominence halves only the mention contribution.
    full = composite_score(1.0, 0.0, 0.0, 1.0)
    half = composite_score(1.0, 0.0, 0.0, 0.5)
    assert round(full, 4) == round(100 * W_MENTION, 4)
    assert round(half, 4) == round(100 * W_MENTION * 0.5, 4)
