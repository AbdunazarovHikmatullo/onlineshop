from django.contrib import admin
from .models import Category, Favorite, Product, ProductAttribute, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'slug')
    list_filter = ('parent',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'is_main', 'order')


class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 3
    fields = ('key', 'value', 'unit')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'brand', 'price', 'stock', 'is_available', 'updated_at')
    list_filter = ('category', 'is_available', 'brand')
    search_fields = ('name', 'sku', 'brand')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_available', 'price', 'stock')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ProductImageInline, ProductAttributeInline]
    fieldsets = (
        ('Основное', {
            'fields': ('category', 'name', 'slug', 'sku', 'brand', 'description'),
        }),
        ('Цена и склад', {
            'fields': ('price', 'stock', 'is_available'),
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('user',)
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at',)
