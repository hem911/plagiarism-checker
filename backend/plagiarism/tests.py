from io import BytesIO
import os
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from docx import Document
import requests
from rest_framework.test import APITestCase

from .google_search import WebSearchConfigurationError, WebSearchServiceError, search_web
from .services import (
    analyze_text,
    build_search_query,
    extract_text_from_file,
    get_similarity_level,
    split_webpage_into_windows,
)


SOURCE_TEXT = (
    'Machine learning is a branch of artificial intelligence that enables computer '
    'systems to learn from examples and improve their performance without explicit '
    'programming.'
)
WEB_RESULT = {
    'title': 'Machine Learning Reference',
    'link': 'https://example.test/machine-learning',
    'snippet': 'A public reference describing machine learning.',
}
LINEAR_SEARCH_TEXT = (
    'Linear search is a sequential searching algorithm where we start from one end '
    'and check every element of the list until the desired element is found. It is '
    'the simplest searching algorithm.'
)


class GoogleSearchServiceTests(APITestCase):
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key', 'GOOGLE_CSE_ID': 'test-cse'}, clear=False)
    @patch('plagiarism.google_search.requests.get')
    def test_google_search_returns_results(self, mock_get):
        response = MagicMock()
        response.json.return_value = {'items': [WEB_RESULT]}
        mock_get.return_value = response

        results = search_web('"machine learning"')

        self.assertEqual(results, [WEB_RESULT])
        self.assertEqual(mock_get.call_args.kwargs['params']['num'], 5)
        self.assertNotIn('test-key', str(results))

    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key', 'GOOGLE_CSE_ID': 'test-cse'}, clear=False)
    @patch('plagiarism.google_search.requests.get')
    def test_google_api_failure_is_safe(self, mock_get):
        mock_get.side_effect = requests.Timeout()

        with self.assertRaises(WebSearchServiceError):
            search_web('"machine learning"')

    @patch.dict(os.environ, {'GOOGLE_API_KEY': '', 'GOOGLE_CSE_ID': ''}, clear=False)
    def test_missing_google_credentials_are_handled(self):
        with self.assertRaisesRegex(WebSearchConfigurationError, 'not configured'):
            search_web('"machine learning"')


class PlagiarismApiTests(APITestCase):
    def test_health_endpoint(self):
        response = self.client.get('/api/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    @patch('plagiarism.services.fetch_page_text', return_value=SOURCE_TEXT)
    @patch('plagiarism.services.search_web', return_value=[WEB_RESULT])
    def test_text_endpoint_preserves_response_contract(self, _search, _fetch):
        response = self.client.post('/api/check-plagiarism/', {'text': SOURCE_TEXT}, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertGreater(response.data['plagiarism_percentage'], 30)
        self.assertEqual(response.data['matches_found'], 1)
        self.assertEqual(
            set(response.data['matches'][0]),
            {'matched_text', 'similarity', 'level', 'source_title', 'source_url', 'source_snippet'},
        )

    @patch('plagiarism.services.fetch_page_text', return_value=SOURCE_TEXT)
    @patch(
        'plagiarism.services.search_web',
        return_value=[WEB_RESULT, {**WEB_RESULT, 'link': 'https://example.test/machine-learning#section'}],
    )
    def test_duplicate_urls_are_fetched_once(self, _search, mock_fetch):
        analyze_text(SOURCE_TEXT)

        mock_fetch.assert_called_once_with('https://example.test/machine-learning')

    @patch('plagiarism.services.fetch_page_text', return_value='')
    @patch('plagiarism.services.search_web', return_value=[WEB_RESULT])
    def test_unreachable_pages_are_skipped(self, _search, _fetch):
        result = analyze_text(SOURCE_TEXT)

        self.assertEqual(result['matches'], [])
        self.assertEqual(result['plagiarism_percentage'], 0.0)

    @patch('plagiarism.services.fetch_page_text', return_value='Astronomy uses telescopes to study distant galaxies.')
    @patch('plagiarism.services.search_web', return_value=[WEB_RESULT])
    def test_unrelated_web_content_has_no_match(self, _search, _fetch):
        result = analyze_text(SOURCE_TEXT)

        self.assertEqual(result['matches_found'], 0)
        self.assertLess(result['plagiarism_percentage'], 30)

    @patch('plagiarism.services.fetch_page_text')
    @patch('plagiarism.services.search_web', return_value=[WEB_RESULT])
    def test_exact_passage_scores_high_against_a_long_page(self, _search, mock_fetch):
        prefix = ' '.join(f'background{index}' for index in range(30))
        suffix = ' '.join(f'additional{index}' for index in range(40))
        mock_fetch.return_value = f'{prefix} {LINEAR_SEARCH_TEXT} {suffix}'

        result = analyze_text(LINEAR_SEARCH_TEXT)

        self.assertGreaterEqual(result['plagiarism_percentage'], 60)
        self.assertEqual(result['matches_found'], 1)
        self.assertEqual(result['matches'][0]['matched_text'], LINEAR_SEARCH_TEXT)

    def test_webpage_windows_overlap(self):
        windows = split_webpage_into_windows(' '.join(f'word{index}' for index in range(90)))

        self.assertGreater(len(windows), 1)
        self.assertIn('word30', windows[0])
        self.assertIn('word30', windows[1])

    def test_short_distinctive_query_is_an_exact_phrase(self):
        query = build_search_query(LINEAR_SEARCH_TEXT)

        self.assertTrue(query.startswith('"'))
        self.assertTrue(query.endswith('"'))

    def test_empty_text_is_rejected(self):
        response = self.client.post('/api/check-plagiarism/', {'text': '   '}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])

    @patch.dict(os.environ, {'GOOGLE_API_KEY': '', 'GOOGLE_CSE_ID': ''}, clear=False)
    def test_unconfigured_web_search_returns_safe_error(self):
        response = self.client.post('/api/check-plagiarism/', {'text': SOURCE_TEXT}, format='json')

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['error'], 'Web search service is not configured.')

    @patch('plagiarism.services.fetch_page_text', return_value=SOURCE_TEXT)
    @patch('plagiarism.services.search_web', return_value=[WEB_RESULT])
    def test_txt_upload(self, _search, _fetch):
        upload = SimpleUploadedFile('sample.txt', SOURCE_TEXT.encode('utf-8'), content_type='text/plain')
        response = self.client.post('/api/check-plagiarism/', {'file': upload}, format='multipart')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

    @patch('plagiarism.services.pdfplumber.open')
    def test_pdf_extraction(self, mock_open):
        pdf = MagicMock()
        pdf.pages = [MagicMock(extract_text=lambda: SOURCE_TEXT)]
        mock_open.return_value.__enter__.return_value = pdf
        upload = SimpleUploadedFile('sample.pdf', b'%PDF-placeholder', content_type='application/pdf')

        self.assertEqual(extract_text_from_file(upload), SOURCE_TEXT)

    def test_docx_extraction(self):
        document, buffer = Document(), BytesIO()
        document.add_paragraph(SOURCE_TEXT)
        document.save(buffer)
        upload = SimpleUploadedFile(
            'sample.docx', buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )

        self.assertEqual(extract_text_from_file(upload), SOURCE_TEXT)

    def test_unsupported_file_is_rejected(self):
        upload = SimpleUploadedFile('sample.csv', b'one,two,three', content_type='text/csv')
        response = self.client.post('/api/check-plagiarism/', {'file': upload}, format='multipart')

        self.assertEqual(response.status_code, 400)
        self.assertIn('Unsupported file type', response.data['error'])

    def test_similarity_level(self):
        self.assertEqual(get_similarity_level(29), 'Low')
        self.assertEqual(get_similarity_level(30), 'Medium')
        self.assertEqual(get_similarity_level(60), 'High')
