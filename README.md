# langchain-crw

[![PyPI version](https://img.shields.io/pypi/v/langchain-crw)](https://pypi.org/project/langchain-crw/)
[![Python](https://img.shields.io/pypi/pyversions/langchain-crw)](https://pypi.org/project/langchain-crw/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

LangChain document loader for [CRW](https://github.com/us/crw) — a high-performance, Firecrawl-compatible web scraper written in Rust.

## Installation

```bash
pip install langchain-crw
# or
uv add langchain-crw
```

That's it. No server to install, no `cargo install`, no Docker. The `crw` SDK automatically downloads and manages the CRW binary for you.

## Quick Start — Zero Config (Subprocess Mode)

```python
from langchain_crw import CrwLoader

# Just works — crw SDK handles everything locally
loader = CrwLoader(url="https://example.com", mode="scrape")
docs = loader.load()
print(docs[0].page_content)  # clean markdown
```

## Cloud Mode ([fastcrw.com](https://fastcrw.com))

No local binary needed. [Sign up at fastcrw.com](https://fastcrw.com) and get **500 free credits**:

```python
from langchain_crw import CrwLoader

loader = CrwLoader(
    url="https://example.com",
    mode="scrape",
    api_url="https://fastcrw.com/api",
    api_key="crw_live_...",  # or set CRW_API_KEY env var
)
docs = loader.load()
```

## Advanced: Self-hosted Server

If you prefer running a persistent CRW server (e.g., shared across services):

```bash
# Option A: Install binary
curl -fsSL https://raw.githubusercontent.com/us/crw/main/install.sh | bash
crw  # starts on http://localhost:3000

# Option B: Docker
docker run -d -p 3000:3000 ghcr.io/us/crw:latest
```

```python
loader = CrwLoader(url="https://example.com", api_url="http://localhost:3000")
```

## Usage

### Scrape a single page

```python
loader = CrwLoader(url="https://example.com", mode="scrape")
docs = loader.load()

print(docs[0].page_content)    # clean markdown
print(docs[0].metadata)        # {'title': '...', 'sourceURL': '...', 'statusCode': 200}
```

### Crawl an entire site

```python
loader = CrwLoader(
    url="https://docs.example.com",
    mode="crawl",
    params={"max_depth": 3, "max_pages": 50},
)
docs = loader.load()
print(f"Crawled {len(docs)} pages")
```

### Discover URLs (map mode)

```python
loader = CrwLoader(url="https://example.com", mode="map")
urls = [doc.page_content for doc in loader.load()]
```

### Search the web (Cloud Only)

> **Cloud-only feature.** Search requires a fastcrw.com API key or a CRW server with SearXNG configured.

```python
from langchain_crw import CrwLoader

loader = CrwLoader(
    query="web scraping tools 2026",
    mode="search",
    api_url="https://fastcrw.com/api",
    api_key="YOUR_KEY",
    params={"limit": 5},
)
docs = loader.load()

for doc in docs:
    print(doc.metadata["title"], doc.metadata["url"])
    print(doc.page_content[:200])
```

### Scrape with JS rendering

```python
loader = CrwLoader(
    url="https://spa-app.example.com",
    mode="scrape",
    params={
        "render_js": True,
        "wait_for": 3000,
        "css_selector": "article.main-content",
    },
)
docs = loader.load()
```

### RAG pipeline

```python
from langchain_crw import CrwLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Crawl docs (self-hosted or cloud — same code)
loader = CrwLoader(url="https://docs.example.com", mode="crawl", params={"max_depth": 3, "max_pages": 50})
docs = loader.load()

# Split and embed
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)
vectorstore = FAISS.from_documents(chunks, OpenAIEmbeddings())

# Query
results = vectorstore.similarity_search("how to authenticate")
```

## Configuration

### Constructor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | `""` | URL to scrape, crawl, or map. Not required for search mode |
| `api_key` | `str \| None` | `None` | Bearer token. Falls back to `CRW_API_KEY` env var |
| `api_url` | `str \| None` | `None` | CRW server URL. Falls back to `CRW_API_URL`. If unset, uses subprocess mode (no server needed) |
| `mode` | `"scrape" \| "crawl" \| "map" \| "search"` | `"scrape"` | Operation mode |
| `query` | `str \| None` | `None` | Search query string. Required for search mode |
| `params` | `dict \| None` | `None` | Additional API parameters |

### Params (snake_case, auto-converted to camelCase)

| Param | Modes | Description |
|-------|-------|-------------|
| `render_js` | scrape | Enable JavaScript rendering |
| `wait_for` | scrape | Wait time in ms after page load |
| `css_selector` | scrape | CSS selector to extract |
| `only_main_content` | scrape, crawl | Extract main content only |
| `max_depth` | crawl, map | Maximum crawl depth |
| `max_pages` | crawl | Maximum pages to crawl |
| `use_sitemap` | map | Use sitemap for URL discovery |
| `poll_interval` | crawl | Poll interval in seconds (default: 2) |
| `timeout` | crawl | Crawl timeout in seconds (default: 300) |

## Migrating from FireCrawlLoader

`CrwLoader` supports the same `scrape`, `crawl`, and `map` modes, plus a `search` mode. Note that `CrwLoader` defaults to `mode="scrape"` while `FireCrawlLoader` defaults to `mode="crawl"` — set the mode explicitly when migrating.

```python
# Before
from langchain_community.document_loaders import FireCrawlLoader
loader = FireCrawlLoader(url="https://example.com", api_key="fc-...", mode="scrape")

# After — pip install langchain-crw, zero config, no server needed
from langchain_crw import CrwLoader
loader = CrwLoader(url="https://example.com", mode="scrape")
```

## License

MIT
