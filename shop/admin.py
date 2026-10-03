from django.contrib import admin

from .models import Product, Purchase


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'price', 'stock']
    search_fields = ['name', 'brand']


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ['product', 'person', 'date']
    readonly_fields = ['product', 'person', 'address', 'date']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
