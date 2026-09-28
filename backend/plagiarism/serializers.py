from rest_framework import serializers


class PlagiarismCheckSerializer(serializers.Serializer):
    """Validate either direct text or an uploaded document."""

    text = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    file = serializers.FileField(required=False, allow_empty_file=True)

    def validate(self, attrs):
        text = attrs.get('text')
        uploaded_file = attrs.get('file')

        if text is None and uploaded_file is None:
            raise serializers.ValidationError('Please provide text or upload a file.')
        if text is not None and not text.strip() and uploaded_file is None:
            raise serializers.ValidationError('Text cannot be empty.')
        return attrs
