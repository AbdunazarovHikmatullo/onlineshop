from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from cart.telegram import get_bot_username
from .forms import LoginForm, RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect('product:index')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth.login(request, user)
            return redirect('product:index')
    else:
        form = RegisterForm()
    return render(request, 'account/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('product:index')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            auth.login(request, form.get_user())
            next_url = request.GET.get('next', '')
            return redirect(next_url or 'product:index')
    else:
        form = LoginForm(request)
    return render(request, 'account/login.html', {'form': form})


def logout_view(request):
    auth.logout(request)
    return redirect('product:index')


@login_required
def profile(request):
    if request.method == 'POST':
        tid = request.POST.get('telegram_id', '').strip()
        if tid and tid.lstrip('-').isdigit():
            request.user.telegram_id = int(tid)
            messages.success(request, 'Telegram подключён — вы будете получать уведомления о заказах.')
        else:
            request.user.telegram_id = None
            messages.success(request, 'Telegram отключён.')
        request.user.save(update_fields=['telegram_id'])
        return redirect('account:profile')
    bot_username = get_bot_username()
    recent_orders = (
        request.user.orders
        .prefetch_related('items__product')
        .order_by('-created_at')[:10]
    )
    return render(request, 'account/profile.html', {
        'bot_username':  bot_username,
        'recent_orders': recent_orders,
    })
