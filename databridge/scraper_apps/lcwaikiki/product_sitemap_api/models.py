from django.db import models

class SitemapSource(models.Model):
    url = models.URLField(max_length=255, default="https://www.lcw.com/sitemap/api/FeedXml/TR/product_sitemap.xml")
    last_fetch = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.url
    
    class Meta:
        verbose_name = "Sitemap Source"
        verbose_name_plural = "Sitemap Source"
        
    def save(self, *args, **kwargs):
        # Sadece bir tane kayıt olmasını sağla
        if not self.pk and SitemapSource.objects.exists():
            return SitemapSource.objects.first()
        return super(SitemapSource, self).save(*args, **kwargs)

class SitemapUrl(models.Model):
    source = models.ForeignKey(SitemapSource, on_delete=models.CASCADE, related_name='urls')
    url = models.URLField(max_length=255)
    last_modification = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.url

    class Meta:
        verbose_name = "Sitemap URL"
        verbose_name_plural = "Sitemap URLs"
        unique_together = ('source', 'url')
