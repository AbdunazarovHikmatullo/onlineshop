from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from product.models import Product
from .cart import Cart
from .models import Order, OrderItem
from .telegram import send_order_confirmation, send_order_notification


def cart_page(request):
    cart = Cart(request)
    return render(request, 'cart/cart.html', {
        'items': cart.get_items(),
        'total': cart.total(),
    })


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_available=True)
    cart = Cart(request)
    quantity = max(1, int(request.POST.get('quantity', 1)))
    cart.add(product_id, quantity)
    return JsonResponse({
        'success': True,
        'count':   cart.count(),
        'message': f'«{product.name}» добавлен в корзину',
    })


@require_POST
def remove_from_cart(request, product_id):
    Cart(request).remove(product_id)
    return redirect('cart:cart')


@require_POST
def update_cart(request, product_id):
    quantity = int(request.POST.get('quantity', 1))
    Cart(request).update(product_id, quantity)
    return redirect('cart:cart')


@login_required
@require_POST
def submit_order(request):
    cart = Cart(request)
    items = cart.get_items()
    if not items:
        return redirect('cart:cart')

    phone = request.POST.get('phone', '').strip()
    if not phone:
        messages.error(request, 'Укажите номер телефона')
        return redirect('cart:cart')

    if request.POST.get('save_phone') and phone and not request.user.phone:
        request.user.phone = phone
        request.user.save(update_fields=['phone'])

    order = Order.objects.create(
        user=request.user,
        phone=phone,
        comment=request.POST.get('comment', '').strip(),
    )
    for item in items:
        OrderItem.objects.create(
            order=order,
            product=item['product'],
            quantity=item['quantity'],
            price=item['product'].price,
        )
    cart.clear()
    send_order_notification(order)
    send_order_confirmation(order)

    return redirect('cart:order_success')


def order_success(request):
    return render(request, 'cart/order_success.html')
