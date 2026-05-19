import json
import urllib.request

TELEGRAM_TOKEN    = '8611866572:AAEM9XMh8dqRVq32W3sWgbMpxluBLZ2Fr-4'
TELEGRAM_OWNER_IDS = [5120430509]

_BOT_USERNAME = None


def get_bot_username():
    global _BOT_USERNAME
    if _BOT_USERNAME:
        return _BOT_USERNAME
    try:
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe'
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
            _BOT_USERNAME = data['result']['username']
    except Exception:
        pass
    return _BOT_USERNAME


def send_order_notification(order):
    """Уведомление владельцу магазина о новом заказе."""
    user = order.user
    full_name = f'{user.first_name} {user.last_name}'.strip() or user.username
    lines = [
        f'🛒 *Новый заказ \\#{order.pk}*\n',
        f'👤 {_esc(full_name)}',
        f'📧 {_esc(user.email or "—")}',
        f'📞 {_esc(order.phone or "не указан")}',
    ]
    if order.comment:
        lines.append(f'💬 {_esc(order.comment)}')
    lines.append('\n*Состав заказа:*')
    total = 0
    for item in order.items.select_related('product').all():
        name = _esc(item.product.name if item.product else 'Удалённый товар')
        subtotal = item.price * item.quantity
        total += subtotal
        lines.append(f'• {name} × {item.quantity} — {_esc(str(int(item.price)))} ₽')
    lines.append(f'\n💰 *Итого: {_esc(str(int(total)))} ₽*')
    text = '\n'.join(lines)
    for owner_id in TELEGRAM_OWNER_IDS:
        _send(owner_id, text)


def send_order_confirmation(order):
    """Подтверждение заказа покупателю (если он привязал Telegram)."""
    if not order.user or not getattr(order.user, 'telegram_id', None):
        return
    lines = [
        f'✅ *Ваш заказ \\#{order.pk} принят\\!*\n',
        'Мы свяжемся с вами для подтверждения\\.\n',
        '*Состав заказа:*',
    ]
    total = 0
    for item in order.items.select_related('product').all():
        name = _esc(item.product.name if item.product else 'Удалённый товар')
        subtotal = item.price * item.quantity
        total += subtotal
        lines.append(f'• {name} × {item.quantity} — {_esc(str(int(item.price)))} ₽')
    lines.append(f'\n💰 *Итого: {_esc(str(int(total)))} ₽*')
    lines.append(f'📞 {_esc(order.phone or "не указан")}')
    text = '\n'.join(lines)
    _send(order.user.telegram_id, text)


def send_status_update(order):
    """Уведомление покупателю об изменении статуса заказа."""
    if not order.user or not getattr(order.user, 'telegram_id', None):
        return
    status_label = dict(order.STATUS_CHOICES).get(order.status, order.status)
    text = (
        f'📦 *Заказ \\#{order.pk}*\n'
        f'Статус изменён: *{_esc(status_label)}*'
    )
    _send(order.user.telegram_id, text)


def _esc(text):
    for ch in r'_*[]()~`>#+-=|{}.!':
        text = str(text).replace(ch, f'\\{ch}')
    return text


def _send(chat_id, text):
    try:
        payload = json.dumps({
            'chat_id':    chat_id,
            'text':       text,
            'parse_mode': 'MarkdownV2',
        }).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        urllib.request.urlopen(req, timeout=6)
    except Exception:
        pass
