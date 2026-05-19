"""
Telegram bot long-polling daemon.

Usage:
    python manage.py run_bot

The bot handles /start <user_pk> to link a user's Telegram account.
Once linked, the user receives order notifications automatically.
"""
import json
import time
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand

from cart.telegram import TELEGRAM_TOKEN, _esc, _send

API = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'

HELP_TEXT = (
    'Привет\\! Я бот магазина *VMARKET*\\.\n\n'
    'Для получения уведомлений о заказах:\n'
    '1\\. Войдите на сайт\n'
    '2\\. Перейдите в раздел *Профиль*\n'
    '3\\. Нажмите кнопку *«Подключить Telegram»*\n\n'
    'Если кнопка открыла этот чат — просто нажмите *START*\\.'
)


class Command(BaseCommand):
    help = 'Run Telegram bot (long polling) to link user accounts and send notifications'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Bot started. Press Ctrl+C to stop.'))
        offset = 0
        while True:
            try:
                updates = self._get_updates(offset)
                for update in updates:
                    offset = update['update_id'] + 1
                    self._handle(update)
            except KeyboardInterrupt:
                self.stdout.write('\nBot stopped.')
                break
            except urllib.error.URLError as e:
                self.stderr.write(f'Network error: {e}. Retrying in 10s...')
                time.sleep(10)
            except Exception as e:
                self.stderr.write(f'Error: {e}')
                time.sleep(5)

    def _get_updates(self, offset):
        url = f'{API}/getUpdates?timeout=30&offset={offset}'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=35) as resp:
            data = json.loads(resp.read())
        return data.get('result', [])

    def _handle(self, update):
        msg = update.get('message') or update.get('edited_message', {})
        if not msg:
            return
        text = msg.get('text', '')
        chat_id = msg.get('chat', {}).get('id')
        if not chat_id:
            return

        self.stdout.write(f'Message from {chat_id}: {text!r}')

        if text.startswith('/start'):
            parts = text.split(maxsplit=1)
            token = parts[1].strip() if len(parts) > 1 else ''
            self._handle_start(chat_id, token)
        else:
            _send(chat_id, HELP_TEXT)

    def _handle_start(self, chat_id, token):
        from account.models import User

        if not token or not token.isdigit():
            _send(chat_id, HELP_TEXT)
            return

        try:
            user = User.objects.get(pk=int(token))
        except User.DoesNotExist:
            _send(chat_id, 'Ссылка недействительна\\. Сгенерируйте новую в профиле сайта\\.')
            return

        user.telegram_id = chat_id
        user.save(update_fields=['telegram_id'])
        name = _esc(user.first_name or user.username)
        _send(
            chat_id,
            f'✅ Аккаунт *{name}* успешно подключён\\!\n\n'
            'Теперь вы будете получать уведомления о заказах и изменении их статуса\\.'
        )
        self.stdout.write(
            self.style.SUCCESS(f'Linked telegram_id={chat_id} to user {user.username} (pk={user.pk})')
        )
