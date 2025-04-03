from rest_framework import serializers
from scraper_apps.lcwaikiki.product_sitemap_api.models import SitemapSource, SitemapUrl

class SitemapUrlSerializer(serializers.ModelSerializer):
    class Meta:
        model = SitemapUrl
        fields = ('url', 'last_modification')

class SitemapSourceSerializer(serializers.ModelSerializer):
    urls = SitemapUrlSerializer(many=True, read_only=True)
    
    class Meta:
        model = SitemapSource
        fields = ('url', 'urls')
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            "source": data['url'],
            "urls": data['urls']
        }