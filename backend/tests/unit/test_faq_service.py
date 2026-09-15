from app.services import faq_service


def test_word_order_independent_matching():
    """Regression test: the original prototype's exact-substring matcher
    missed "my wallet balance is negative" because "negative balance" only
    appears reordered in the text. Matching must be word-set based."""
    faq = faq_service.search("my wallet balance is negative")
    assert faq is not None
    assert faq.id == "negative_balance"


def test_exact_phrase_match():
    faq = faq_service.search("I cannot hear the other person on the call")
    assert faq is not None
    assert faq.id == "cannot_hear"


def test_no_match_for_unrelated_text():
    assert faq_service.search("what is the weather today") is None


def test_audience_filter_excludes_listener_only_faq_for_user():
    faq = faq_service.search("not getting calls", audience="user")
    assert faq is None or faq.id != "not_getting_calls"


def test_gibberish_detection():
    assert faq_service.looks_like_gibberish("qwrtsplk")
    assert not faq_service.looks_like_gibberish("hello there")


def test_looks_app_related():
    assert faq_service.looks_app_related("my coins got deducted")
    assert not faq_service.looks_app_related("tell me a joke about cats")
