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

## Setup — Pick One

### Option A: Cloud ([fastcrw.com](https://fastcrw.com)) — Quickest Start

No server to install. [Sign up at fastcrw.com](https://fastcrw.com) and get **500 free credits** to start scraping:

```bash
export CRW_API_KEY=crw_live_...  # get yours at fastcrw.com
```

```python
from langchain_crw import CrwLoader

# Cloud is the default — just set CRW_API_KEY and go
loader = CrwLoader(url="https://example.com", mode="scrape")
docs = loader.load()
print(docs[0].page_content)  # clean markdown
```

### Option B: Self-hosted with binary (free, no limits)

Single binary, ~15 MB download, ~6 MB idle RAM. No Docker needed.

```bash
curl -fsSL https://raw.githubusercontent.com/us/crw/main/install.sh | bash
crw  # starts on http://localhost:3000
```

```python
loader = CrwLoader(url="https://example.com", api_url="http://localhost:3000")
```

### Option C: Self-hosted with Docker

```bash
docker run -d -p 3000:3000 ghcr.io/us/crw:latest
```

```python
loader = CrwLoader(url="https://example.com", api_url="http://localhost:3000")
```

```python
from langchain_crw import CrwLoader

# No api_key needed — auto-connects to localhost:3000
loader = CrwLoader(url="https://example.com", mode="scrape")
docs = loader.load()
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
| `url` | `str` | required | URL to scrape, crawl, or map |
| `api_key` | `str \| None` | `None` | Bearer token. Falls back to `CRW_API_KEY` env var |
| `api_url` | `str \| None` | `None` | CRW server URL. Falls back to `CRW_API_URL`, then `http://localhost:3000` |
| `mode` | `"scrape" \| "crawl" \| "map"` | `"scrape"` | Operation mode |
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

`CrwLoader` supports the same `scrape`, `crawl`, and `map` modes. Note that `CrwLoader` defaults to `mode="scrape"` while `FireCrawlLoader` defaults to `mode="crawl"` — set the mode explicitly when migrating.

```python
# Before
from langchain_community.document_loaders import FireCrawlLoader
loader = FireCrawlLoader(url="https://example.com", api_key="fc-...", mode="scrape")

# After — similar interface, self-hosted, no SDK needed
from langchain_crw import CrwLoader
loader = CrwLoader(url="https://example.com", mode="scrape")
```

## License

MIT
