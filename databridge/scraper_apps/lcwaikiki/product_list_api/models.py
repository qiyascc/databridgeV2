from django.db import models

class ProductListSource(models.Model):
    url = models.URLField(max_length=255, default="")
    last_modification = models.DateField(null=True, blank=True)
    last_fetch = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.url
    
    class Meta:
        verbose_name = "Product List Source"
        verbose_name_plural = "Product List Sources"
        
class ProductUrl(models.Model):
    source = models.ForeignKey(ProductListSource, on_delete=models.CASCADE, related_name='product_urls')
    url = models.URLField(max_length=255)
    change_frequency = models.CharField(max_length=50, blank=True, null=True)
    priority = models.CharField(max_length=10, blank=True, null=True)
    lcw_last_modification = models.DateField(null=True, blank=True)
    system_last_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.url

    class Meta:
        verbose_name = "Product URL"
        verbose_name_plural = "Product URLs"
        unique_together = ('source', 'url')