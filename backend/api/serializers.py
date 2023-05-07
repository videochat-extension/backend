from rest_framework import serializers

class GeoRequestSerializer(serializers.Serializer):
    ip = serializers.IPAddressField()
    lang = serializers.CharField(min_length=2, max_length=5)

    def validate(self, attrs):
        if attrs['lang'] not in ["en", 'de', 'es', 'pt-BR', 'fr', 'ja', 'zh-CN', 'ru']:
            attrs['lang'] = 'en'
        return attrs