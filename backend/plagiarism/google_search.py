"""Small, bounded Google Programmable Search and page-fetching client."""

import os
import re
from urllib.parse import urldefrag

import requests
from lxml import etree, html


GOOGLE_SEARCH_URL = 'https://www.googleapis.com/customsearch/v1'
RESULTS_PER_QUERY = 5
MAX_SOURCE_PAGES = 10
REQUEST_TIMEOUT_SECONDS = 10
MAX_PAGE_TEXT_LENGTH = 100000
USER_AGENT = 'Mozilla/5.0 (compatible; OnlinePlagiarismChecker/1.0)'


class WebSearchConfigurationError(RuntimeError):
    """Raised when Google Programmable Search credentials are unavailable."""


class WebSearchServiceError(RuntimeError):
    """Raised when Google Search cannot safely complete a request."""


def _credentials():
    """Read credentials at call time so environment-based configuration is honoured."""
    api_key = os.getenv('GOOGLE_API_KEY', '').strip()
    search_engine_id = os.getenv('GOOGLE_CSE_ID', '').strip()
    if not api_key or not search_engine_id:
        raise WebSearchConfigurationError('Web search service is not configured.')
    return api_key, search_engine_id


def normalize_url(url):
    """Return a comparable HTTP(S) URL without a fragment, or an empty string."""
    if not isinstance(url, str):
        return ''
    normalized_url = url.strip()
    if not normalized_url.startswith(('http://', 'https://')):
        return ''
    return urldefrag(normalized_url)[0]


def search_web(query):
    """Return title/link/snippet records from one Google Programmable Search query."""
    api_key, search_engine_id = _credentials()
    try:
        response = requests.get(
            GOOGLE_SEARCH_URL,
            params={
                'key': api_key,
                'cx': search_engine_id,
                'q': query,
                'num': RESULTS_PER_QUERY,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise WebSearchServiceError('Web search service is temporarily unavailable.') from exc

    if not isinstance(payload, dict):
        raise WebSearchServiceError('Web search service is temporarily unavailable.')

    items = payload.get('items', [])
    if items is None:
        return []
    if not isinstance(items, list):
        raise WebSearchServiceError('Web search service is temporarily unavailable.')

    results = []
    for item in items[:RESULTS_PER_QUERY]:
        if not isinstance(item, dict):
            continue
        link = normalize_url(item.get('link'))
        if not link:
            continue
        results.append(
            {
                'title': str(item.get('title') or link),
                'link': link,
                'snippet': str(item.get('snippet') or ''),
            }
        )
    return results


def fetch_page_text(url):
    """Fetch visible text from one public HTML page, returning an empty string on failure."""
    try:
        response = requests.get(
            url,
            headers={'User-Agent': USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        document = html.fromstring(response.content)
        for element in document.xpath('//script|//style|//noscript'):
            element.drop_tree()
        text = re.sub(r'\s+', ' ', document.text_content()).strip()
        return text[:MAX_PAGE_TEXT_LENGTH]
    except (requests.RequestException, ValueError, TypeError, etree.ParserError):
        return ''
