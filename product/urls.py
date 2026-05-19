from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    path('',                              views.index,          name='index'),
    path('catalog/',                      views.catalog,        name='catalog'),
    path('catalog/<slug:slug>/',          views.product_detail, name='detail'),
    path('product/add/',                  views.product_add,    name='product_add'),
    path('product/<slug:slug>/edit/',     views.product_edit,   name='product_edit'),
    path('product/<slug:slug>/delete/',   views.product_delete, name='product_delete'),
    path('dashboard/',                    views.dashboard,      name='dashboard'),
    path('favorites/',                    views.favorites,      name='favorites'),
    path('favorites/toggle/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
]