"""Text extraction and web-source similarity helpers for the MVP."""

import re
from pathlib import Path

import pdfplumber
from docx import Document
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .google_search import (
    MAX_SOURCE_PAGES,
    fetch_page_text,
    normalize_url,
    search_web,
)


SIMILARITY_THRESHOLD = 0.30
MEDIUM_MATCH_MIN_PERCENT = 30
HIGH_MATCH_MIN_PERCENT = 60
MAX_SEARCH_QUERIES = 5
MIN_CHUNK_WORDS = 15
MAX_CHUNK_WORDS = 40
MAX_QUERY_WORDS = 32
MAX_QUERY_CHARACTERS = 240
WEB_WINDOW_WORDS = 60
WEB_WINDOW_OVERLAP = 30


class FileExtractionError(ValueError):
    """Raised when an uploaded document cannot provide usable text."""


def extract_text_from_file(uploaded_file):
    """Extract text from an in-memory TXT, PDF, or DOCX upload."""
    if not uploaded_file or not uploaded_file.name:
        raise FileExtractionError('Please upload a valid file.')
    if uploaded_file.size == 0:
        raise FileExtractionError('The uploaded file is empty.')

    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in {'.txt', '.pdf', '.docx'}:
        raise FileExtractionError('Unsupported file type. Use TXT, PDF, or DOCX.')

    try:
        uploaded_file.seek(0)
        if extension == '.txt':
            text = uploaded_file.read().decode('utf-8-sig')
        elif extension == '.pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        else:
            document = Document(uploaded_file)
            text = '\n'.join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        raise FileExtractionError('Could not extract text from the uploaded file.') from exc

    cleaned_text = clean_text(text)
    if not cleaned_text:
        raise FileExtractionError('The uploaded file does not contain readable text.')
    return cleaned_text


def clean_text(text):
    """Normalize whitespace while leaving words and punctuation unchanged."""
    if not text:
        return ''
    normalized_newlines = str(text).replace('\r\n', '\n').replace('\r', '\n')
    return re.sub(r'\s+', ' ', normalized_newlines).strip()


def split_into_chunks(text):
    """Build useful 15-40 word chunks without requiring an NLP dependency."""
    cleaned_text = clean_text(text)
    if not cleaned_text:
        return []
    sentences = [sentence.strip() for sentence in re.split(r'(?<=[.!?])\s+', cleaned_text) if sentence.strip()]
    chunks, current_words = [], []
    for sentence in sentences:
        sentence_words = sentence.split()
        if current_words and len(current_words) + len(sentence_words) > MAX_CHUNK_WORDS:
            chunks.append(' '.join(current_words))
            current_words = []
        current_words.extend(sentence_words)
        if len(current_words) >= MIN_CHUNK_WORDS:
            chunks.append(' '.join(current_words))
            current_words = []
    if current_words:
        if chunks and len(current_words) < MIN_CHUNK_WORDS:
            chunks[-1] = f"{chunks[-1]} {' '.join(current_words)}"
        else:
            chunks.append(' '.join(current_words))
    return chunks


def get_similarity_level(score):
    """Return a human-readable level for a percentage score."""
    if score >= HIGH_MATCH_MIN_PERCENT:
        return 'High'
    if score >= MEDIUM_MATCH_MIN_PERCENT:
        return 'Medium'
    return 'Low'


def build_search_query(chunk):
    """Use a bounded quoted phrase so one request stays meaningful to Google."""
    words = clean_text(chunk).split()[:MAX_QUERY_WORDS]
    phrase = ' '.join(words)[:MAX_QUERY_CHARACTERS].strip()
    return f'"{phrase}"' if phrase else ''


def select_distinctive_chunks(chunks):
    """Choose only the most vocabulary-rich chunks, capped to protect API quota."""
    def distinctiveness(chunk):
        words = re.findall(r"\b[\w'-]{3,}\b", chunk.lower())
        return (len(set(words)), len(words))

    return sorted(chunks, key=distinctiveness, reverse=True)[:MAX_SEARCH_QUERIES]


def split_webpage_into_windows(page_text):
    """Create overlapping page sections so long pages do not dilute a passage match."""
    words = clean_text(page_text).split()
    if not words:
        return []
    if len(words) <= WEB_WINDOW_WORDS:
        return [' '.join(words)]

    step = WEB_WINDOW_WORDS - WEB_WINDOW_OVERLAP
    return [
        ' '.join(words[start:start + WEB_WINDOW_WORDS])
        for start in range(0, len(words), step)
    ]


def _best_window_similarity(chunk, windows):
    """Return the highest TF-IDF cosine score and its matching source window."""
    if not windows:
        return 0.0, ''
    try:
        # Fitting chunk + all windows together lets cosine similarity compare the
        # submitted text to every small page section without whole-page dilution.
        matrix = TfidfVectorizer().fit_transform([chunk, *windows])
    except ValueError:
        return 0.0, ''
    scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()
    best_index = scores.argmax()
    return float(scores[best_index]), windows[best_index]


def _find_web_sources(search_chunks):
    """Search at most five phrases and fetch at most ten distinct accessible pages."""
    search_results, seen_urls = [], set()
    for chunk in search_chunks:
        query = build_search_query(chunk)
        if not query:
            continue
        for result in search_web(query):
            url = normalize_url(result['link'])
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            search_results.append({**result, 'link': url})
            if len(search_results) >= MAX_SOURCE_PAGES:
                break
        if len(search_results) >= MAX_SOURCE_PAGES:
            break

    sources = []
    for result in search_results:
        page_text = fetch_page_text(result['link'])
        if page_text:
            sources.append({**result, 'windows': split_webpage_into_windows(page_text)})
    return sources


def analyze_text(text):
    """Compare submitted content against accessible Google-discovered web pages."""
    cleaned_text = clean_text(text)
    chunks = split_into_chunks(cleaned_text)
    if not chunks:
        return {
            'plagiarism_percentage': 0.0,
            'total_words': 0,
            'total_chunks': 0,
            'matches_found': 0,
            'matches': [],
        }

    sources = _find_web_sources(select_distinctive_chunks(chunks))
    source_matches, best_score_by_chunk = [], [0.0] * len(chunks)
    for source in sources:
        strongest_score, strongest_chunk_index, strongest_window = 0.0, None, ''
        for index, chunk in enumerate(chunks):
            score, matched_window = _best_window_similarity(chunk, source['windows'])
            if score > best_score_by_chunk[index]:
                best_score_by_chunk[index] = score
            if score > strongest_score:
                strongest_score, strongest_chunk_index, strongest_window = score, index, matched_window
        if strongest_chunk_index is None or strongest_score < SIMILARITY_THRESHOLD:
            continue
        # Retained internally for traceability; the public contract remains unchanged.
        source['matched_window'] = strongest_window
        percentage = round(strongest_score * 100, 1)
        source_matches.append(
            {
                'matched_text': chunks[strongest_chunk_index],
                'similarity': percentage,
                'level': get_similarity_level(percentage),
                'source_title': source['title'],
                'source_url': source['link'],
                'source_snippet': source['snippet'],
            }
        )

    # Each chunk contributes only its strongest real page comparison; unmatched
    # chunks contribute zero. This prevents result ranking from inflating a score.
    plagiarism_percentage = max(0.0, min(100.0, sum(best_score_by_chunk) / len(chunks) * 100))
    matches = source_matches
    matches.sort(key=lambda match: match['similarity'], reverse=True)

    return {
        'plagiarism_percentage': round(plagiarism_percentage, 1),
        'total_words': len(re.findall(r"\b[\w'-]+\b", cleaned_text)),
        'total_chunks': len(chunks),
        'matches_found': len(matches),
        'matches': matches,
    }
