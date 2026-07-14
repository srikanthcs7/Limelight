from app.providers.serpapi_provider import extract_aio_result
from tests.fixtures import SERPAPI_AIO_RESPONSE, SERPAPI_NO_AIO


def test_extract_aio_answer_and_citations():
    result = extract_aio_result(SERPAPI_AIO_RESPONSE)
    assert "GetQuizSolve" in result.answer_text
    assert "Coursology" in result.answer_text  # list item folded in
    domains = {c.domain for c in result.cited_urls}
    assert domains == {"reddit.com", "getquizsolve.com"}
    assert result.raw is SERPAPI_AIO_RESPONSE


def test_extract_no_aio_is_empty_but_valid():
    result = extract_aio_result(SERPAPI_NO_AIO)
    assert result.answer_text == ""
    assert result.cited_urls == []
    assert result.raw is SERPAPI_NO_AIO
