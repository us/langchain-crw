# langchain-crw

[![PyPI version](https://img.shields.io/pypi/v/langchain-crw)](https://pypi.org/project/langchain-crw/)
[![Python](https://img.shields.io/pypi/pyversions/langchain-crw)](https://pypi.org/project/langchain-crw/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

LangChain document loader for [CRW](https://github.com/us/crw), a high-performance, Firecrawl-compatible web scraper written in Rust.

## Installation

```bash
pip install langchain-crw
# or
uv add langchain-crw
```

This package re-exports the loader from the `crw` SDK, so `pip install 'crw[langchain]'` gives you the identical `CrwLoader`. Use whichever name fits your dependency list.

## Quick Start (Cloud)

CRW is cloud-first. [Sign up at fastcrw.com](https://fastcrw.com/dashboard) for **500 free credits** (no card, one time, never expires) and set `CRW_API_KEY`:

```bash
export CRW_API_KEY="crw_live_..."
```

```python
from langchain_crw import CrwLoader

loader = CrwLoader(url="https://example.com", mode="scrape")
docs = loader.load()
print(docs[0].page_content)  # clean markdown
```

You can also pass the key directly:

```python
loader = CrwLoader(url="https://example.com", api_key="crw_live_...")
```

## Local Engine (no key, no server)

Set `CRW_LOCAL=1` and the SDK downloads and manages a checksum-verified CRW binary for you, then talks to it over a subprocess. No account and no server to run, and your URLs and scraped content never reach fastCRW (the engine still fetches the pages it scrapes):

```bash
export CRW_LOCAL=1
```

```python
loader = CrwLoader(url="https://example.com", mode="scrape")  # same code
```

`CRW_LOCAL=1` takes precedence over `api_url`. If both are set the local engine wins and `api_url` is ignored.

## Self-hosted Server

If you would rather run a persistent CRW server, shared across services:

```bash
# Option A: Install the binary
curl -fsSL https://fastcrw.com/install | sh
crw serve  # listens on http://localhost:3000

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

### Search the web

Search needs a backend: the managed cloud provides one, and a self-hosted server needs one configured.

```python
loader = CrwLoader(
    query="web scraping tools 2026",
    mode="search",
    params={"limit": 5},
)
docs = loader.load()

for doc in docs:
    print(doc.metadata["title"], doc.metadata["url"])
    print(doc.page_content[:200])
```

### Parse a local PDF

`parse` mode takes a local file path in `url` rather than a web address.

```python
loader = CrwLoader(url="report.pdf", mode="parse")
docs = loader.load()
```

`params` may carry `formats`, `json_schema`, and `parsers`.

### Structured extraction

`extract` mode runs LLM extraction across one or more URLs. `query` is the prompt and `params["schema"]` is the JSON Schema. Requires cloud or a server, not the local engine.

```python
loader = CrwLoader(
    url=["https://example.com/pricing"],
    mode="extract",
    query="Extract the plan names and monthly prices",
    params={"schema": {"type": "object", "properties": {"plans": {"type": "array"}}}},
)
docs = loader.load()  # page_content is JSON, metadata carries url, status, error
```

Optional `params`: `llm_api_key`, `llm_provider`, `llm_model`.

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

# Crawl docs. Cloud, local engine, and self-hosted all run the same code.
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
| `url` | `str \| list[str]` | `""` | URL to scrape, crawl, map, or extract from. A local file path in `parse` mode. Not required for `search` |
| `api_key` | `str \| None` | `None` | Bearer token. Falls back to `CRW_API_KEY`. Not needed with `CRW_LOCAL=1` or an unauthenticated self-hosted server |
| `api_url` | `str \| None` | `None` | CRW server URL. Falls back to `CRW_API_URL`. If unset, the managed cloud at `api.fastcrw.com` is used. Ignored when `CRW_LOCAL=1` |
| `mode` | `"scrape" \| "crawl" \| "map" \| "search" \| "parse" \| "extract"` | `"scrape"` | Operation mode |
| `query` | `str \| None` | `None` | Search query in `search` mode, extraction prompt in `extract` mode |
| `params` | `dict \| None` | `None` | Additional parameters, forwarded to the SDK |

### Params

Named parameters are translated to the API's camelCase. Anything else is forwarded verbatim, so you can pass API fields directly.

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
| `schema` | extract | JSON Schema for the extracted object |
| `formats`, `json_schema`, `parsers` | parse | PDF parsing options |

## Migrating from FireCrawlLoader

`CrwLoader` supports the same `scrape`, `crawl`, and `map` modes, plus `search`, `parse`, and `extract`. Note that `CrwLoader` defaults to `mode="scrape"` while `FireCrawlLoader` defaults to `mode="crawl"`, so set the mode explicitly when migrating.

```python
# Before
from langchain_community.document_loaders import FireCrawlLoader
loader = FireCrawlLoader(url="https://example.com", api_key="fc-...", mode="scrape")

# After
from langchain_crw import CrwLoader
loader = CrwLoader(url="https://example.com", mode="scrape")
```

## License

MIT
