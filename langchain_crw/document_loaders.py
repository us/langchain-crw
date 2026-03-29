"""CRW document loader for LangChain.

Security note: Do not pass untrusted user input to ``url``, ``api_url``,
``headers``, or ``proxy`` parameters. These are forwarded as HTTP requests
and could be used for SSRF if exposed to untrusted input.
"""

from __future__ import annotations

import os
from typing import Any, Iterator, Literal, Optional

from crw import CrwClient
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document


class CrwLoader(BaseLoader):
    """Load documents using CRW web scraper.

    CRW is a high-performance, Firecrawl-compatible web scraper written in Rust.
    Self-hosted (crw-server) or cloud (fastcrw.com).

    Setup:
        Install the package:

        .. code-block:: bash

            pip install langchain-crw

        The ``crw`` SDK will automatically download and manage the crw-mcp binary,
        so no server setup is required. For remote/cloud usage, provide an api_url.

    Instantiate:
        .. code-block:: python

            from langchain_crw import CrwLoader

            # Subprocess mode (zero config, no server needed — default)
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
                Not required for subprocess mode or self-hosted without auth.
            api_url: Base URL of CRW server for HTTP mode.
                Read from CRW_API_URL env var if not provided.
                Defaults to None (subprocess mode — spawns crw-mcp binary).
            mode: Operation mode - "scrape", "crawl", or "map".
            params: Additional parameters passed to the CRW API.
        """
        self.url = url
        self.api_key = api_key or os.getenv("CRW_API_KEY")
        self.api_url = api_url or os.getenv("CRW_API_URL") or None
        self.mode = mode
        self.params = params or {}
        self._client: Optional[CrwClient] = None

    def _get_client(self) -> CrwClient:
        """Get or create the CrwClient instance."""
        if self._client is None:
            self._client = CrwClient(
                api_url=self.api_url,
                api_key=self.api_key,
            )
        return self._client

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
        client = self._get_client()
        kwargs = self._build_sdk_params()
        result = client.scrape(self.url, **kwargs)

        if not result:
            return

        doc = self._parse_document(result)
        if doc.page_content:
            yield doc

    def _crawl(self) -> Iterator[Document]:
        """Crawl a site and yield documents."""
        client = self._get_client()
        kwargs = self._build_sdk_params()

        # Extract poll/timeout params
        poll_interval = max(self.params.get("poll_interval", 2.0), 0.1)
        timeout = max(self.params.get("timeout", 300.0), 0)

        pages = client.crawl(
            self.url,
            poll_interval=poll_interval,
            timeout=timeout,
            **kwargs,
        )

        for page in pages:
            doc = self._parse_document(page)
            if doc.page_content:
                yield doc

    def _map(self) -> Iterator[Document]:
        """Discover URLs on a site."""
        client = self._get_client()
        kwargs = self._build_sdk_params()
        links = client.map(self.url, **kwargs)

        for link in links:
            if isinstance(link, str) and link:
                yield Document(page_content=link, metadata={})

    def _build_sdk_params(self) -> dict[str, Any]:
        """Build keyword arguments for CrwClient methods.

        Passes params through as snake_case kwargs. The CrwClient SDK
        handles camelCase conversion internally.
        """
        # Keys handled separately (not forwarded to SDK methods)
        skip_keys = {"poll_interval", "timeout"}

        result: dict[str, Any] = {}
        for key, value in self.params.items():
            if key not in skip_keys:
                result[key] = value
        return result

    def close(self) -> None:
        """Clean up the underlying CrwClient."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __del__(self) -> None:
        self.close()

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
