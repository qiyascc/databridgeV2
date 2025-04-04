from django.contrib import admin
from .models import SitemapSource, SitemapUrl
from unfold.admin import ModelAdmin, StackedInline, TabularInline

class SitemapUrlInline(TabularInline):
    model = SitemapUrl
    extra = 0

@admin.register(SitemapSource)
class SitemapSourceAdmin(ModelAdmin):
    list_display = ('url', 'last_fetch')
    inlines = [SitemapUrlInline]
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        from .views import update_sitemap
        custom_urls = [
            path('update-sitemap/', update_sitemap, name='update_sitemap'),
        ]
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        # Eğer kayıt yoksa, default kayıt oluştur
        if not SitemapSource.objects.exists():
            SitemapSource.objects.create()
            
        # Admin sayfasını görüntülemek yerine edit sayfasına yönlendir
        obj = SitemapSource.objects.first()
        from django.shortcuts import redirect
        from django.urls import reverse
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        url_name = f"admin:{app_label}_{model_name}_change"
        return redirect(reverse(url_name, args=[obj.id]))