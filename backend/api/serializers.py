from django.conf import settings
from rest_framework import serializers
from rest_framework.serializers import ValidationError

class GeoRequestSerializer(serializers.Serializer):
    ip = serializers.IPAddressField()
    lang = serializers.CharField(min_length=2, max_length=5)

    def validate(self, attrs):
        if attrs['lang'] not in ["en", 'de', 'es', 'pt-BR', 'fr', 'ja', 'zh-CN', 'ru']:
            attrs['lang'] = 'en'
        return attrs

class BugReportSerializer(serializers.Serializer):
    secret = serializers.CharField()
    title = serializers.CharField(max_length=200)
    details = serializers.CharField(max_length=200)

    def validate(self, attrs):
        if attrs['secret'] != settings.GH_SECRET:
            raise ValidationError('bad secret')
        return attrs
