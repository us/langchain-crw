"""CRW document loader for LangChain.

Security note: Do not pass untrusted user input to ``url``, ``api_url``,
``headers``, or ``proxy`` parameters. These are forwarded as HTTP requests
and could be used for SSRF if exposed to untrusted input.
"""

from __future__ import annotations

import os
import time
from typing import Any, Iterator, Literal, Optional

import requests
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

_DEFAULT_HTTP_TIMEOUT = 120  # seconds


class CrwLoader(BaseLoader):
    """Load documents using CRW web scraper.

    CRW is a high-performance, Firecrawl-compatible web scraper written in Rust.
    Self-hosted (crw-server) or cloud (fastcrw.com).

    Setup:
        Install the package:

        .. code-block:: bash

            pip install langchain-crw

        Start CRW locally:

        .. code-block:: bash

            curl -fsSL https://raw.githubusercontent.com/us/crw/main/install.sh | bash
            crw

        Or use fastCRW cloud with an API key from https://fastcrw.com.

    Instantiate:
        .. code-block:: python

            from langchain_crw import CrwLoader

            # Self-hosted (no API key needed)
            loader = CrwLoader(url="https://example.com", mode="scrape")

            # Cloud (fastcrw.com)
            loader = CrwLoader(
                url="https://example.com",
                api_key="your-key",
                api_url="https://fastcrw.com/api",
                mode="crawl",
            )

    Lazy load:
        .. code-block:: python

            for doc in loader.lazy_load():
                print(doc.page_content[:100])
                print(doc.metadata)
    """

    def __init__(
        self,
        url: str,
        *,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        mode: Literal["scrape", "crawl", "map"] = "scrape",
        params: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize CrwLoader.

        Args:
            url: The URL to scrape, crawl, or map.
            api_key: Bearer token for authentication.
                Read from CRW_API_KEY env var if not provided.
                Not required for self-hosted without auth.
            api_url: Base URL of CRW server.
                Read from CRW_API_URL env var if not provided.
                Defaults to http://localhost:3000.
            mode: Operation mode - "scrape", "crawl", or "map".
            params: Additional parameters passed to the CRW API.
        """
        self.url = url
        self.api_key = api_key or os.getenv("CRW_API_KEY")
        self.api_url = (
            api_url or os.getenv("CRW_API_URL") or "http://localhost:3000"
        ).rstrip("/")
        self.mode = mode
        self.params = params or {}
        self._session = requests.Session()
        if self.api_key:
            self._session.headers["Authorization"] = f"Bearer {self.api_key}"
        self._session.headers["Content-Type"] = "application/json"

    def lazy_load(self) -> Iterator[Document]:
        """Lazy load documents from CRW."""
        if self.mode == "scrape":
            yield from self._scrape()
        elif self.mode == "crawl":
            yield from self._crawl()
        elif self.mode == "map":
            yield from self._map()
        else:
            raise ValueError(
                f"Invalid mode '{self.mode}'. Must be 'scrape', 'crawl', or 'map'."
            )

    def _scrape(self) -> Iterator[Document]:
        """Scrape a single URL."""
        body: dict[str, Any] = {"url": self.url}
        body.update(self._build_api_params())
        response = self._request("POST", "/v1/scrape", json=body)

        data = response.get("data", {})
        if not data:
            return

        doc = self._parse_document(data)
        if doc.page_content:
            yield doc

    def _crawl(self) -> Iterator[Document]:
        """Crawl a site via async job polling."""
        body: dict[str, Any] = {"url": self.url}
        body.update(self._build_api_params())

        start_response = self._request("POST", "/v1/crawl", json=body)
        job_id = start_response.get("id")
        if not job_id:
            raise ValueError(
                f"CRW crawl did not return a job ID. Response: {start_response}"
            )

        poll_interval = max(self.params.get("poll_interval", 2), 0.1)
        timeout = max(self.params.get("timeout", 300), 0)
        elapsed = 0.0

        while elapsed < timeout:
            status_response = self._request("GET", f"/v1/crawl/{job_id}")
            status = status_response.get("status")

            if status == "completed":
                for page in status_response.get("data", []):
                    doc = self._parse_document(page)
                    if doc.page_content:
                        yield doc
                # Handle pagination if server returns next URL
                next_url = status_response.get("next")
                while next_url:
                    next_resp = self._request("GET", "", _full_url=next_url)
                    for page in next_resp.get("data", []):
                        doc = self._parse_document(page)
                        if doc.page_content:
                            yield doc
                    next_url = next_resp.get("next")
                return

            if status == "failed":
                raise RuntimeError(
                    f"CRW crawl job '{job_id}' failed. "
                    f"Response: {status_response}"
                )

            if status not in ("scraping", "queued", "waiting"):
                raise RuntimeError(
                    f"CRW crawl job '{job_id}' returned unexpected status "
                    f"'{status}'. Response: {status_response}"
                )

            time.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(
            f"CRW crawl job '{job_id}' timed out after {timeout}s."
        )

    def _map(self) -> Iterator[Document]:
        """Discover URLs on a site."""
        body: dict[str, Any] = {"url": self.url}
        body.update(self._build_api_params())
        response = self._request("POST", "/v1/map", json=body)

        # Links may be at top level or nested under "data"
        links = response.get("links") or response.get("data", {}).get("links", [])
        for link in links:
            if isinstance(link, str) and link:
                yield Document(page_content=link, metadata={})

    def _build_api_params(self) -> dict[str, Any]:
        """Convert snake_case params to camelCase API fields."""
        mapping = {
            "formats": "formats",
            "only_main_content": "onlyMainContent",
            "render_js": "renderJs",
            "wait_for": "waitFor",
            "include_tags": "includeTags",
            "exclude_tags": "excludeTags",
            "headers": "headers",
            "css_selector": "cssSelector",
            "xpath": "xpath",
            "json_schema": "jsonSchema",
            "proxy": "proxy",
            "stealth": "stealth",
            "max_depth": "maxDepth",
            "max_pages": "maxPages",
            "use_sitemap": "useSitemap",
        }
        result: dict[str, Any] = {}
        for key, value in self.params.items():
            api_key = mapping.get(key, key)
            if key in ("poll_interval", "timeout"):
                continue
            result[api_key] = value
        return result

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[dict[str, Any]] = None,
        _full_url: Optional[str] = None,
    ) -> dict[str, Any]:
        """Make HTTP request to CRW API."""
        url = _full_url or f"{self.api_url}{path}"
        response = self._session.request(
            method, url, json=json, timeout=_DEFAULT_HTTP_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _parse_document(page: dict[str, Any]) -> Document:
        """Convert a CRW page response to a LangChain Document."""
        content = (
            page.get("markdown")
            or page.get("html")
            or page.get("rawHtml")
            or page.get("plainText")
            or ""
        )
        # Ensure content is a string
        if not isinstance(content, str):
            content = str(content)
        metadata = page.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        return Document(page_content=content, metadata=metadata)
