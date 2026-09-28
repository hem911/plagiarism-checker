from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import PlagiarismCheckSerializer
from .google_search import WebSearchConfigurationError, WebSearchServiceError
from .services import FileExtractionError, analyze_text, clean_text, extract_text_from_file


def _serializer_error_message(errors):
    """Return the first serializer error as a concise API error message."""
    first_error = next(iter(errors.values()))
    return str(first_error[0])


@api_view(['GET'])
def health(request):
    return Response({'status': 'ok'})


@api_view(['POST'])
def check_plagiarism(request):
    serializer = PlagiarismCheckSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'success': False, 'error': _serializer_error_message(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        text = serializer.validated_data.get('text')
        if text is None or not text.strip():
            text = extract_text_from_file(serializer.validated_data.get('file'))
        else:
            text = clean_text(text)

        if not text:
            return Response(
                {'success': False, 'error': 'Text cannot be empty.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({'success': True, **analyze_text(text)})
    except FileExtractionError as exc:
        return Response(
            {'success': False, 'error': str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except WebSearchConfigurationError as exc:
        return Response(
            {'success': False, 'error': str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except WebSearchServiceError as exc:
        return Response(
            {'success': False, 'error': str(exc)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception:
        return Response(
            {'success': False, 'error': 'Unable to process the submitted content.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
