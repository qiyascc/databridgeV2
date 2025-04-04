from django.contrib import admin
from .models import ProductListSource, ProductUrl
from unfold.admin import ModelAdmin, StackedInline, TabularInline

class ProductUrlInline(TabularInline):
    model = ProductUrl
    extra = 0
    readonly_fields = ('url', 'change_frequency', 'priority', 'lcw_last_modification', 'system_last_modification')
    can_delete = False
    show_change_link = True
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(ProductListSource)
class ProductListSourceAdmin(ModelAdmin):
    list_display = ('url', 'last_modification', 'last_fetch')
    inlines = [ProductUrlInline]
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        from .views import update_product_list
        custom_urls = [
            path('update-product-list/', update_product_list, name='update_product_list'),
        ]
        return custom_urls + urls

@admin.register(ProductUrl)
class ProductUrlAdmin(ModelAdmin):
    list_display = ('url', 'source', 'change_frequency', 'priority', 'lcw_last_modification', 'system_last_modification')
    list_filter = ('source', 'change_frequency', 'priority', 'lcw_last_modification')
    search_fields = ('url',)
    readonly_fields = ('system_last_modification',)