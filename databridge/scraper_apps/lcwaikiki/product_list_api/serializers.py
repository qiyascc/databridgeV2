from rest_framework import serializers
from scraper_apps.lcwaikiki.product_list_api.models import ProductUrl

class ProductUrlSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductUrl
        fields = ('id', 'url', 'source', 'change_frequency', 'priority', 'lcw_last_modification', 'system_last_modification')

class ProductUrlListSerializer(serializers.ModelSerializer):
    source = serializers.StringRelatedField()
    
    class Meta:
        model = ProductUrl
        fields = ('id', 'url', 'source', 'change_frequency', 'priority', 'lcw_last_modification', 'system_last_modification')
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            "id": data['id'],
            "url": data['url'],
            "source": data['source'],
            "change_frequency": data['change_frequency'],  # Hata düzeltilmiş hali
            "priority": data['priority'],
            "lcw_last_modification": data['lcw_last_modification'],
            "system_last_modification": data['system_last_modification'],
        }

class FilteredProductUrlSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductUrl
        fields = ('id', 'url', 'change_frequency', 'priority', 'lcw_last_modification', 'system_last_modification')
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        return {
            "id": data['id'],
            "url": data['url'],
            "change_frequency": data['change_frequency'],
            "priority": data['priority'],
            "lcw_last_modification": data['lcw_last_modification'],
            "system_last_modification": data['system_last_modification'],
        }

class OnlyUrlsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductUrl
        fields = ('id', 'url',)
    
    def to_representation(self, instance):
        return {
            "id": instance.id,
            "url": instance.url
        }
