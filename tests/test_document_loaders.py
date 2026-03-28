"""Tests for CrwLoader."""

import os
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from langchain_crw import CrwLoader


@pytest.fixture
def mock_session():
    with patch("langchain_crw.document_loaders.requests.Session") as mock_cls:
        session = MagicMock()
        session.headers = {}
        mock_cls.return_value = session
        yield session


class TestInit:
    def test_default_api_url(self, mock_session):
        loader = CrwLoader(url="https://example.com")
        assert loader.api_url == "https://fastcrw.com/api"

    def test_custom_api_url(self, mock_session):
        loader = CrwLoader(url="https://example.com", api_url="https://fastcrw.com/api")
        assert loader.api_url == "https://fastcrw.com/api"

    def test_trailing_slash_stripped(self, mock_session):
        loader = CrwLoader(url="https://example.com", api_url="https://fastcrw.com/api/")
        assert loader.api_url == "https://fastcrw.com/api"

    def test_api_key_set_in_header(self, mock_session):
        CrwLoader(url="https://example.com", api_key="test-key")
        assert mock_session.headers["Authorization"] == "Bearer test-key"

    def test_no_api_key_no_auth_header(self, mock_session):
        CrwLoader(url="https://example.com")
        assert "Authorization" not in mock_session.headers

    @patch.dict(os.environ, {"CRW_API_KEY": "env-key"})
    def test_api_key_from_env(self, mock_session):
        loader = CrwLoader(url="https://example.com")
        assert loader.api_key == "env-key"

    @patch.dict(os.environ, {"CRW_API_URL": "https://env-url.com"})
    def test_api_url_from_env(self, mock_session):
        loader = CrwLoader(url="https://example.com")
        assert loader.api_url == "https://env-url.com"


class TestScrape:
    def test_scrape_returns_document(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "markdown": "# Hello World",
                "metadata": {"title": "Hello", "sourceURL": "https://example.com"},
            },
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.request.return_value = mock_response

        loader = CrwLoader(url="https://example.com", mode="scrape")
        docs = list(loader.lazy_load())

        assert len(docs) == 1
        assert docs[0].page_content == "# Hello World"
        assert docs[0].metadata["title"] == "Hello"

    def test_scrape_with_params(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": {"markdown": "ok", "metadata": {}}}
        mock_response.raise_for_status = MagicMock()
        mock_session.request.return_value = mock_response

        loader = CrwLoader(
            url="https://example.com",
            mode="scrape",
            params={"render_js": True, "css_selector": "article"},
        )
        list(loader.lazy_load())

        body = mock_session.request.call_args[1]["json"]
        assert body["renderJs"] is True
        assert body["cssSelector"] == "article"

    def test_scrape_empty_data_yields_nothing(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_response.raise_for_status = MagicMock()
        mock_session.request.return_value = mock_response

        loader = CrwLoader(url="https://example.com", mode="scrape")
        assert list(loader.lazy_load()) == []

    def test_scrape_fallback_to_html(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {"html": "<h1>Hi</h1>", "metadata": {}},
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.request.return_value = mock_response

        loader = CrwLoader(url="https://example.com", mode="scrape")
        docs = list(loader.lazy_load())
        assert docs[0].page_content == "<h1>Hi</h1>"


class TestCrawl:
    def test_crawl_returns_documents(self, mock_session):
        start = MagicMock()
        start.json.return_value = {"success": True, "id": "job-1"}
        start.raise_for_status = MagicMock()

        completed = MagicMock()
        completed.json.return_value = {
            "status": "completed",
            "data": [
                {"markdown": "# Page 1", "metadata": {"sourceURL": "https://example.com"}},
                {"markdown": "# Page 2", "metadata": {"sourceURL": "https://example.com/about"}},
            ],
        }
        completed.raise_for_status = MagicMock()

        mock_session.request.side_effect = [start, completed]

        loader = CrwLoader(url="https://example.com", mode="crawl")
        docs = list(loader.lazy_load())

        assert len(docs) == 2
        assert docs[0].page_content == "# Page 1"
        assert docs[1].metadata["sourceURL"] == "https://example.com/about"

    @patch("langchain_crw.document_loaders.time.sleep")
    def test_crawl_polls(self, mock_sleep, mock_session):
        start = MagicMock()
        start.json.return_value = {"success": True, "id": "job-2"}
        start.raise_for_status = MagicMock()

        scraping = MagicMock()
        scraping.json.return_value = {"status": "scraping"}
        scraping.raise_for_status = MagicMock()

        done = MagicMock()
        done.json.return_value = {"status": "completed", "data": [{"markdown": "# Done", "metadata": {}}]}
        done.raise_for_status = MagicMock()

        mock_session.request.side_effect = [start, scraping, done]

        loader = CrwLoader(url="https://example.com", mode="crawl")
        docs = list(loader.lazy_load())

        assert len(docs) == 1
        mock_sleep.assert_called_once_with(2)

    def test_crawl_failed(self, mock_session):
        start = MagicMock()
        start.json.return_value = {"success": True, "id": "job-fail"}
        start.raise_for_status = MagicMock()

        failed = MagicMock()
        failed.json.return_value = {"status": "failed"}
        failed.raise_for_status = MagicMock()

        mock_session.request.side_effect = [start, failed]

        loader = CrwLoader(url="https://example.com", mode="crawl")
        with pytest.raises(RuntimeError, match="failed"):
            list(loader.lazy_load())

    @patch("langchain_crw.document_loaders.time.sleep")
    def test_crawl_timeout(self, mock_sleep, mock_session):
        start = MagicMock()
        start.json.return_value = {"success": True, "id": "job-slow"}
        start.raise_for_status = MagicMock()

        scraping = MagicMock()
        scraping.json.return_value = {"status": "scraping"}
        scraping.raise_for_status = MagicMock()

        mock_session.request.side_effect = [start] + [scraping] * 200

        loader = CrwLoader(url="https://example.com", mode="crawl", params={"timeout": 4, "poll_interval": 2})
        with pytest.raises(TimeoutError):
            list(loader.lazy_load())


class TestMap:
    def test_map_returns_urls(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "links": ["https://example.com", "https://example.com/about"],
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.request.return_value = mock_response

        loader = CrwLoader(url="https://example.com", mode="map")
        docs = list(loader.lazy_load())

        assert len(docs) == 2
        assert docs[0].page_content == "https://example.com"

    def test_map_skips_empty(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "links": ["https://example.com", ""]}
        mock_response.raise_for_status = MagicMock()
        mock_session.request.return_value = mock_response

        loader = CrwLoader(url="https://example.com", mode="map")
        assert len(list(loader.lazy_load())) == 1


class TestInterface:
    def test_lazy_load_returns_iterator(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": {"markdown": "# Test", "metadata": {}}}
        mock_response.raise_for_status = MagicMock()
        mock_session.request.return_value = mock_response

        loader = CrwLoader(url="https://example.com")
        assert isinstance(loader.lazy_load(), Iterator)

    def test_load_returns_list(self, mock_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": {"markdown": "# Test", "metadata": {}}}
        mock_response.raise_for_status = MagicMock()
        mock_session.request.return_value = mock_response

        loader = CrwLoader(url="https://example.com")
        result = loader.load()
        assert isinstance(result, list)

    def test_invalid_mode(self, mock_session):
        loader = CrwLoader(url="https://example.com")
        loader.mode = "invalid"
        with pytest.raises(ValueError, match="Invalid mode"):
            list(loader.lazy_load())
