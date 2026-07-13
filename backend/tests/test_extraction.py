from app.providers.openai_provider import domain_of, extract_engine_result
from tests.fixtures import RESPONSES_WEB_SEARCH_DUMP


def test_domain_of():
    assert domain_of("https://a.b.getquizsolve.com/x?y=1") == "getquizsolve.com"
    assert domain_of("https://www.reddit.com/r/college") == "reddit.com"


def test_extract_answer_text():
    result = extract_engine_result(RESPONSES_WEB_SEARCH_DUMP)
    assert "GetQuizSolve" in result.answer_text
    assert "Coursology" in result.answer_text


def test_extract_citations_and_domains():
    result = extract_engine_result(RESPONSES_WEB_SEARCH_DUMP)
    domains = [c.domain for c in result.cited_urls]
    # Both reddit citations present pre-dedup (dedup happens in the citations step).
    assert domains.count("reddit.com") == 2
    assert "getquizsolve.com" in domains


def test_extract_falls_back_when_no_output_text_key():
    result = extract_engine_result(RESPONSES_WEB_SEARCH_DUMP)
    # fixture has no top-level output_text -> reconstructed from message content
    assert result.answer_text.startswith("For online courses")
