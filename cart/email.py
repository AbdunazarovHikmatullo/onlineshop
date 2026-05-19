from django.core.mail import send_mail

# Цвета статусов (text / background)
_STATUS_COLORS = {
    'pending':     ('#b8860b', '#fff8e1'),
    'confirmed':   ('#1565c0', '#e3f2fd'),
    'in_progress': ('#2e7d32', '#e8f5e9'),
    'ready':       ('#6a1b9a', '#f3e5f5'),
    'completed':   ('#1b5e20', '#e8f5e9'),
    'cancelled':   ('#b71c1c', '#fce4ec'),
}


def send_status_email(order):
    """Отправляет HTML-письмо покупателю при смене статуса заказа."""
    if not order.user or not order.user.email:
        return
    subject = f'Заказ #{order.pk} — статус обновлён'
    html = _build_html(order)
    try:
        send_mail(
            subject=subject,
            message=_build_plain(order),
            from_email=None,  # DEFAULT_FROM_EMAIL из settings
            recipient_list=[order.user.email],
            html_message=html,
            fail_silently=True,
        )
    except Exception:
        pass


def _build_plain(order):
    status_label = dict(order.STATUS_CHOICES).get(order.status, order.status)
    lines = [f'Заказ #{order.pk} — {status_label}', '', 'Состав:']
    total = 0
    for item in order.items.select_related('product').all():
        name = item.product.name if item.product else 'Удалённый товар'
        sub = item.price * item.quantity
        total += sub
        lines.append(f'  {name} × {item.quantity} — {int(item.price)} ₽')
    lines.append(f'\nИтого: {int(total)} ₽')
    return '\n'.join(lines)


def _build_html(order):
    status_label = dict(order.STATUS_CHOICES).get(order.status, order.status)
    fg, bg = _STATUS_COLORS.get(order.status, ('#333', '#f5f5f5'))

    # Build items rows
    rows_html = ''
    total = 0
    for item in order.items.select_related('product').all():
        name = item.product.name if item.product else 'Удалённый товар'
        sub = item.price * item.quantity
        total += sub
        rows_html += f'''
        <tr>
          <td style="padding:10px 16px;border-bottom:1px solid #e8e8e8;font-size:14px;color:#333;">{_esc(name)}</td>
          <td style="padding:10px 16px;border-bottom:1px solid #e8e8e8;font-size:14px;color:#666;text-align:center;">{item.quantity}</td>
          <td style="padding:10px 16px;border-bottom:1px solid #e8e8e8;font-size:14px;color:#333;text-align:right;white-space:nowrap;">{int(item.price):,} ₽</td>
          <td style="padding:10px 16px;border-bottom:1px solid #e8e8e8;font-size:14px;font-weight:600;color:#0f0f0f;text-align:right;white-space:nowrap;">{int(sub):,} ₽</td>
        </tr>'''

    user = order.user
    name_display = user.get_full_name() or user.username

    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Заказ #{order.pk}</title>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">

  <!-- Wrapper -->
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr>
          <td style="background:#e84000;padding:28px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <span style="font-size:22px;font-weight:800;color:#ffffff;letter-spacing:-.5px;">V<span style="opacity:.85">MARKET</span></span>
                </td>
                <td align="right">
                  <span style="font-size:12px;color:rgba(255,255,255,.75);">Автозапчасти</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px 0;">

            <p style="margin:0 0 6px;font-size:13px;color:#717171;text-transform:uppercase;letter-spacing:.08em;font-weight:700;">
              Уведомление о заказе
            </p>
            <h1 style="margin:0 0 24px;font-size:22px;font-weight:800;color:#0f0f0f;letter-spacing:-.02em;">
              Статус вашего заказа изменён
            </h1>

            <!-- Order info card -->
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#fafafa;border:1px solid #e8e8e8;border-radius:6px;margin-bottom:28px;">
              <tr>
                <td style="padding:20px 24px;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td>
                        <p style="margin:0 0 4px;font-size:12px;color:#717171;text-transform:uppercase;letter-spacing:.07em;font-weight:700;">Номер заказа</p>
                        <p style="margin:0;font-size:20px;font-weight:800;color:#0f0f0f;">#{order.pk}</p>
                      </td>
                      <td align="right">
                        <span style="display:inline-block;padding:6px 14px;border-radius:20px;background:{bg};color:{fg};font-size:13px;font-weight:700;">
                          {_esc(status_label)}
                        </span>
                      </td>
                    </tr>
                  </table>
                  <hr style="border:none;border-top:1px solid #e8e8e8;margin:14px 0;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="font-size:13px;color:#717171;">Покупатель</td>
                      <td align="right" style="font-size:13px;font-weight:600;color:#0f0f0f;">{_esc(name_display)}</td>
                    </tr>
                    {"" if not order.phone else f'''
                    <tr>
                      <td style="font-size:13px;color:#717171;padding-top:6px;">Телефон</td>
                      <td align="right" style="font-size:13px;font-weight:600;color:#0f0f0f;padding-top:6px;">{_esc(order.phone)}</td>
                    </tr>'''}
                  </table>
                </td>
              </tr>
            </table>

            <!-- Items table -->
            <p style="margin:0 0 12px;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#717171;">
              Состав заказа
            </p>
            <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8e8e8;border-radius:6px;overflow:hidden;margin-bottom:28px;">
              <thead>
                <tr style="background:#fafafa;">
                  <th style="padding:10px 16px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#717171;border-bottom:1px solid #e8e8e8;">Товар</th>
                  <th style="padding:10px 16px;text-align:center;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#717171;border-bottom:1px solid #e8e8e8;">Кол-во</th>
                  <th style="padding:10px 16px;text-align:right;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#717171;border-bottom:1px solid #e8e8e8;">Цена</th>
                  <th style="padding:10px 16px;text-align:right;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#717171;border-bottom:1px solid #e8e8e8;">Сумма</th>
                </tr>
              </thead>
              <tbody>
                {rows_html}
                <tr style="background:#fafafa;">
                  <td colspan="3" style="padding:12px 16px;font-size:14px;font-weight:700;color:#0f0f0f;border-top:2px solid #e8e8e8;">Итого</td>
                  <td style="padding:12px 16px;font-size:16px;font-weight:800;color:#e84000;text-align:right;border-top:2px solid #e8e8e8;white-space:nowrap;">{int(total):,} ₽</td>
                </tr>
              </tbody>
            </table>

            <!-- CTA -->
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:36px;">
              <tr>
                <td align="center">
                  <a href="http://127.0.0.1:8000/" style="display:inline-block;padding:13px 32px;background:#e84000;color:#ffffff;font-size:15px;font-weight:700;border-radius:4px;text-decoration:none;letter-spacing:-.01em;">
                    Перейти на сайт
                  </a>
                </td>
              </tr>
            </table>

          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#fafafa;border-top:1px solid #e8e8e8;padding:20px 40px;">
            <p style="margin:0;font-size:12px;color:#aaa;text-align:center;line-height:1.6;">
              © 2024 VMARKET — Автозапчасти оптом и в розницу<br>
              Это автоматическое письмо, отвечать на него не нужно.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>

</body>
</html>'''


def _esc(text):
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))
