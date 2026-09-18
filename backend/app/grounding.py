import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    url: str = ''
    publisher: str = ''
    snippet: str = ''
    published_at: str | None = None
    fetched_at: str | None = None
    source_type: str = 'web'
    document_id: str | None = None
    file_name: str | None = None
    page: int | None = None


def extract_urls(text: str) -> list[str]:
    return re.findall(r'https?://[^\s<>"\u3002，。！？]+', text)


def _clean_url(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return ''
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in {'fbclid', 'gclid'}]
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or '/', urlencode(query), ''))


def normalize_sources(items: list[dict], query: str = '') -> list[Source]:
    seen: set[str] = set()
    result: list[Source] = []
    for index, item in enumerate(items):
        url = _clean_url(str(item.get('url', '')))
        snippet = str(item.get('content') or item.get('raw_content') or '').strip()
        if not url or url in seen or not snippet:
            continue
        seen.add(url)
        host = urlsplit(url).netloc
        result.append(Source(
            id=f's{len(result) + 1}', title=str(item.get('title') or host), url=url,
            publisher=host, snippet=snippet[:2000],
            published_at=item.get('published_at'), fetched_at=item.get('fetched_at'),
        ))
    return result
