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

You also need a CRW backend:

```bash
# Self-hosted (free)
curl -fsSL https://raw.githubusercontent.com/us/crw/main/install.sh | bash
crw  # starts on http://localhost:3000

# Or use fastCRW cloud: https://fastcrw.com
```

## Quick Start

### Scrape a single page

```python
from langchain_crw import CrwLoader

loader = CrwLoader(url="https://example.com", mode="scrape")
docs = loader.load()

print(docs[0].page_content)    # clean markdown
print(docs[0].metadata)        # title, sourceURL, statusCode
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

### Cloud mode (fastCRW)

```python
loader = CrwLoader(
    url="https://example.com",
    api_key="your-key",              # or set CRW_API_KEY env var
    api_url="https://fastcrw.com/api",  # or set CRW_API_URL env var
)
docs = loader.load()
```

### RAG pipeline

```python
from langchain_crw import CrwLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Crawl docs
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

```python
# Before
from langchain_community.document_loaders import FireCrawlLoader
loader = FireCrawlLoader(url="https://example.com", api_key="fc-...", mode="scrape")

# After — same interface, self-hosted, no SDK needed
from langchain_crw import CrwLoader
loader = CrwLoader(url="https://example.com", mode="scrape")
```

## License

MIT
