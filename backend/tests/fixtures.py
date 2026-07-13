"""A realistic OpenAI Responses API (web_search) response dict, shaped like
`response.model_dump()`. Used to test extraction + the full pipeline without a
live API call. The exact live shape is confirmed against the real API in the
user's environment (M1 handoff)."""

RESPONSES_WEB_SEARCH_DUMP = {
    "id": "resp_abc123",
    "model": "gpt-4o",
    "object": "response",
    "output": [
        {
            "id": "ws_1",
            "type": "web_search_call",
            "status": "completed",
            "action": {"type": "search", "query": "best AI study helper Chrome extension"},
        },
        {
            "id": "msg_1",
            "type": "message",
            "role": "assistant",
            "status": "completed",
            "content": [
                {
                    "type": "output_text",
                    "text": (
                        "For online courses, GetQuizSolve is a popular AI study helper "
                        "Chrome extension. Coursology and QuizAce are common alternatives, "
                        "and CheatMate is also mentioned by students."
                    ),
                    "annotations": [
                        {
                            "type": "url_citation",
                            "url": "https://www.reddit.com/r/college/comments/xyz",
                            "title": "Best study extensions",
                            "start_index": 10,
                            "end_index": 40,
                        },
                        {
                            "type": "url_citation",
                            "url": "https://getquizsolve.com/features",
                            "title": "GetQuizSolve features",
                            "start_index": 41,
                            "end_index": 70,
                        },
                        {
                            "type": "url_citation",
                            # duplicate URL -> must be deduped by the citations step
                            "url": "https://www.reddit.com/r/college/comments/xyz",
                            "title": "Best study extensions",
                            "start_index": 80,
                            "end_index": 95,
                        },
                    ],
                }
            ],
        },
    ],
}
