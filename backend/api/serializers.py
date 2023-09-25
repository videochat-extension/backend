from django.conf import settings
from rest_framework import serializers
from rest_framework.serializers import ValidationError
from users.models import User

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

class GeoPatronRequestSerializer(serializers.Serializer):
    ip = serializers.IPAddressField()
    lang = serializers.CharField(min_length=2, max_length=5)
    requestWired = serializers.BooleanField()
    requestCellural = serializers.BooleanField()

    def validate(self, attrs):
        if attrs['lang'] not in ["en", 'de', 'es', 'pt-BR', 'fr', 'ja', 'zh-CN', 'ru']:
            attrs['lang'] = 'en'

        attrs['lang_ipapi'] = attrs['lang']
        attrs['lang_bdc'] = attrs['lang']

        if attrs['lang_bdc'] == 'pt-BR':
            attrs['lang_bdc'] = 'pt'

        if attrs['lang_bdc'] == 'zh-CN':
            attrs['lang_bdc'] = 'cn'

        return attrs


class UserSerializer(serializers.ModelSerializer):
    # snippets = serializers.PrimaryKeyRelatedField(many=True, queryset=Snippet.objects.all())

    class Meta:
        model = User
        fields = ['id', 'username']
