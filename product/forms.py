from django import forms
from django.forms import inlineformset_factory

from .models import Category, Product, ProductAttribute, ProductImage


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'dash-input', 'placeholder': 'Например: Тормозная система',
                'autocomplete': 'off',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'dash-input', 'placeholder': 'tormoznaya-sistema',
                'autocomplete': 'off', 'id': 'id_cat_slug',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].required = False
        self.fields['parent'].empty_label = 'Нет (корневая категория)'
        self.fields['parent'].widget.attrs['class'] = 'dash-input'


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'category', 'name', 'slug', 'sku', 'brand',
            'description', 'price', 'stock', 'is_available',
        ]
        widgets = {
            'slug':        forms.TextInput(attrs={'id': 'id_slug', 'autocomplete': 'off'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['brand'].required = False
        self.fields['description'].required = False
        self.fields['stock'].initial = 0
        for name, field in self.fields.items():
            if name != 'is_available':
                field.widget.attrs.setdefault('class', 'form-input')


ProductAttributeFormSet = inlineformset_factory(
    Product, ProductAttribute,
    fields=['key', 'value', 'unit'],
    extra=1, can_delete=True,
)
