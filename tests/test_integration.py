"""Integration tests that hit the real fastcrw.com API."""

from __future__ import annotations

import os
from typing import Iterator

import pytest
from langchain_core.documents import Document

from langchain_crw import CrwLoader

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("CRW_API_KEY"),
        reason="CRW_API_KEY not set",
    ),
]

API_URL = "https://fastcrw.com/api"


def _api_key() -> str:
    return os.environ["CRW_API_KEY"]


def test_scrape_real_url():
    loader = CrwLoader(
        url="https://example.com",
        mode="scrape",
        api_url=API_URL,
        api_key=_api_key(),
    )
    docs = loader.load()

    assert isinstance(docs, list)
    assert len(docs) > 0
    assert isinstance(docs[0], Document)
    assert len(docs[0].page_content) > 0


@pytest.mark.xfail(reason="crw client crawl polling has a known bug with list response")
def test_crawl_real_url():
    loader = CrwLoader(
        url="https://example.com",
        mode="crawl",
        api_url=API_URL,
        api_key=_api_key(),
        params={"max_pages": 2, "timeout": 60},
    )
    docs = loader.load()

    assert isinstance(docs, list)
    assert len(docs) > 0
    assert all(isinstance(d, Document) for d in docs)


def test_map_real_url():
    loader = CrwLoader(
        url="https://example.com",
        mode="map",
        api_url=API_URL,
        api_key=_api_key(),
    )
    docs = loader.load()

    assert isinstance(docs, list)
    assert len(docs) > 0
    # Each document's page_content should be a URL
    assert all("http" in d.page_content for d in docs)


@pytest.mark.skip(reason="CrwClient does not yet expose a search() method")
def test_search_real_query():
    loader = CrwLoader(
        url="",
        mode="search",
        query="python web scraping",
        api_url=API_URL,
        api_key=_api_key(),
    )
    docs = loader.load()

    assert isinstance(docs, list)
    assert len(docs) > 0
    assert all(isinstance(d, Document) for d in docs)
    # Search results should have title in metadata
    assert "title" in docs[0].metadata


def test_lazy_load_is_iterator():
    loader = CrwLoader(
        url="https://example.com",
        mode="scrape",
        api_url=API_URL,
        api_key=_api_key(),
    )
    result = loader.lazy_load()

    assert isinstance(result, Iterator)
    # Consume the iterator
    docs = list(result)
    assert len(docs) > 0
