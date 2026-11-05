from unittest.mock import patch
from src.information_search import search_information


def test_empty_topic():
    try:
        search_information("")
        assert False, "Expected ValueError"
    except ValueError:
        assert True


@patch("src.information_search.wikipedia.search")
def test_search_returns_no_results(mock_search):
    mock_search.return_value = []

    try:
        search_information("Unknown research topic")
        assert False, "Expected RuntimeError"
    except RuntimeError:
        assert True