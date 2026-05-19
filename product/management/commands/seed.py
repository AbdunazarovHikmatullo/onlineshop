"""
python manage.py seed          — создать всё с нуля
python manage.py seed --clear  — сначала очистить, потом создать
"""
import os
import random
import shutil
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from cart.models import Order, OrderItem
from product.models import Category, Favorite, Product, ProductAttribute, ProductImage

User = get_user_model()

# ── Transliteration ────────────────────────────────────────
_RU = {'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
       'з':'z','и':'i','й':'j','к':'k','л':'l','м':'m','н':'n','о':'o',
       'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts',
       'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'}

def _slug(text):
    t = ''.join(_RU.get(c, c) for c in text.lower())
    return slugify(t) or slugify(text)

def _unique_slug(base, model):
    slug, n = base, 1
    while model.objects.filter(slug=slug).exists():
        slug = f'{base}-{n}'; n += 1
    return slug

# ── Reference data ─────────────────────────────────────────
BRANDS = ['Bosch','Denso','NGK','Brembo','Monroe','KYB','Mann','Mahle',
          'SKF','Valeo','Sachs','Febi','Lemforder','TRW','Delphi','Hella',
          'Gates','Continental','ZF','Moog']

CATEGORY_TREE = {
    'Двигатель':        ['Поршни и гильзы','Прокладки двигателя'],
    'Тормозная система':['Тормозные колодки','Тормозные диски'],
    'Подвеска':         ['Амортизаторы','Пружины и опоры'],
    'Электрика':        ['Аккумуляторы','Генераторы и стартеры'],
    'Трансмиссия':      ['ШРУС и приводы','Сцепление'],
    'Охлаждение':       ['Радиаторы','Помпы охлаждения'],
    'Выхлопная система':['Катализаторы','Глушители'],
    'Рулевое управление':['Рулевые рейки','Наконечники рулевые'],
    'Топливная система':['Топливные насосы','Форсунки'],
    'Кузов':            ['Бамперы','Крылья и двери'],
}

# (name, category_name, attrs)
PRODUCTS = [
    # Двигатель
    ('Поршень двигателя D83mm',   'Поршни и гильзы',
     [('Диаметр','83','мм'),('Материал','алюминиевый сплав','')]),
    ('Прокладка ГБЦ Multi-Layer', 'Прокладки двигателя',
     [('Слоёв','3','шт.'),('Толщина','1.5','мм')]),
    ('Клапан впускной 35мм',      'Поршни и гильзы',
     [('Тип','впускной',''),('Диаметр тарелки','35','мм')]),
    ('Поршневые кольца комплект', 'Поршни и гильзы',
     [('Диаметр','82','мм'),('В комплекте','4 шт','')]),

    # Тормоза
    ('Колодки тормозные передние', 'Тормозные колодки',
     [('Позиция','передние',''),('Материал','керамика','')]),
    ('Колодки тормозные задние',   'Тормозные колодки',
     [('Позиция','задние',''),('С датчиком износа','да','')]),
    ('Диск тормозной вентилируемый 300мм','Тормозные диски',
     [('Диаметр','300','мм'),('Тип','вентилируемый',''),('Толщина','28','мм')]),
    ('Диск тормозной сплошной 260мм',    'Тормозные диски',
     [('Диаметр','260','мм'),('Тип','сплошной','')]),
    ('Суппорт тормозной передний левый', 'Тормозные диски',
     [('Сторона','левый',''),('Позиция','передний','')]),

    # Подвеска
    ('Амортизатор передний газомасляный', 'Амортизаторы',
     [('Тип','газомасляный',''),('Позиция','передний',''),('Ход','200','мм')]),
    ('Амортизатор задний масляный',       'Амортизаторы',
     [('Тип','масляный',''),('Позиция','задний','')]),
    ('Пружина подвески передняя',         'Пружины и опоры',
     [('Жёсткость','средняя',''),('Высота','340','мм')]),
    ('Опора стойки с подшипником',        'Пружины и опоры',
     [('Включает подшипник','да','')]),
    ('Стойка стабилизатора передняя',     'Амортизаторы',
     [('Длина','320','мм'),('Позиция','передняя','')]),
    ('Рычаг подвески нижний левый',       'Амортизаторы',
     [('Позиция','нижний левый',''),('Материал','сталь','')]),

    # Электрика
    ('Аккумулятор 60Ач 540A',     'Аккумуляторы',
     [('Ёмкость','60','Ач'),('Пусковой ток','540','А'),('Полярность','прямая','')]),
    ('Аккумулятор 77Ач 780A EFB', 'Аккумуляторы',
     [('Ёмкость','77','Ач'),('Тип','EFB',''),('Пусковой ток','780','А')]),
    ('Генератор 120А',            'Генераторы и стартеры',
     [('Ток','120','А'),('Напряжение','14','В')]),
    ('Стартер 1.4 кВт',           'Генераторы и стартеры',
     [('Мощность','1.4','кВт'),('Напряжение','12','В')]),
    ('Свечи зажигания иридиевые (4шт)', 'Генераторы и стартеры',
     [('Тип','иридиевые',''),('В упаковке','4','шт.')]),

    # Трансмиссия
    ('ШРУС наружный левый',        'ШРУС и приводы',
     [('Зубьев','25','шт.'),('Сторона','левый','')]),
    ('ШРУС наружный правый',       'ШРУС и приводы',
     [('Зубьев','25','шт.'),('Сторона','правый','')]),
    ('Диск сцепления 228мм',       'Сцепление',
     [('Диаметр','228','мм'),('Зубьев','22','шт.')]),
    ('Корзина сцепления 228мм',    'Сцепление',
     [('Диаметр','228','мм'),('Тип','нажимной диск','')]),
    ('Подшипник выжимной',         'Сцепление',
     [('Тип','нажимной','')]),

    # Охлаждение
    ('Радиатор охлаждения алюминиевый','Радиаторы',
     [('Материал','алюминий',''),('Рядов','2','')]),
    ('Термостат 87°C',               'Радиаторы',
     [('Температура открытия','87','°C')]),
    ('Помпа охлаждения',             'Помпы охлаждения',
     [('Диаметр крыльчатки','60','мм')]),
    ('Расширительный бачок',         'Помпы охлаждения',
     [('Объём','1.2','л')]),

    # Выхлопная
    ('Катализатор передний',    'Катализаторы',
     [('Тип','трёхкомпонентный',''),('Сечение','55','мм')]),
    ('Глушитель задний',        'Глушители',
     [('Диаметр трубы','60','мм'),('Материал','нержавейка','')]),

    # Рулевое
    ('Рейка рулевая гидравлическая','Рулевые рейки',
     [('Тип','гидравлическая',''),('Передаточное число','16.4','')]),
    ('Наконечник рулевой левый',    'Наконечники рулевые',
     [('Сторона','левый','')]),
    ('Наконечник рулевой правый',   'Наконечники рулевые',
     [('Сторона','правый','')]),
    ('Тяга рулевая',                'Наконечники рулевые',
     [('Длина','475','мм')]),

    # Топливная
    ('Топливный насос погружной',  'Топливные насосы',
     [('Давление','3.5','бар'),('Производительность','100','л/ч')]),
    ('Регулятор давления топлива', 'Топливные насосы',
     [('Давление','3.0','бар')]),
    ('Форсунка топливная 6 отв.',  'Форсунки',
     [('Отверстий','6','шт.'),('Тип','электромагнитная','')]),
    ('Топливный фильтр',           'Форсунки',
     [('Давление','10','бар'),('Нить фильтрации','10','мкм')]),

    # Кузов
    ('Бампер передний грунтованный','Бамперы',
     [('Позиция','передний',''),('Цвет','под покраску','')]),
    ('Крыло переднее правое',       'Крылья и двери',
     [('Сторона','правое',''),('Позиция','переднее','')]),
]

FIRST_NAMES = ['Александр','Дмитрий','Иван','Михаил','Сергей',
               'Алексей','Андрей','Артём','Кирилл','Николай',
               'Анна','Мария','Елена','Ольга','Наталья',
               'Татьяна','Екатерина','Юлия','Ирина','Светлана']
LAST_NAMES  = ['Иванов','Смирнов','Кузнецов','Попов','Васильев',
               'Петров','Соколов','Михайлов','Новиков','Федоров',
               'Морозов','Волков','Алексеев','Лебедев','Семёнов',
               'Егоров','Павлов','Козлов','Степанов','Николаев']


class Command(BaseCommand):
    help = 'Заполнить БД синтетическими данными'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='Удалить существующие данные перед заполнением')

    def handle(self, *args, **options):
        if options['clear']:
            self._clear()

        images = self._collect_images()
        self.stdout.write(f'Найдено изображений: {len(images)}')

        self._seed_admin()
        categories = self._seed_categories()
        products   = self._seed_products(categories, images)
        users      = self._seed_users()
        self._seed_orders(users, products)
        self._seed_favorites(users, products)

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Создано: {len(categories)} категорий, {len(products)} товаров, '
            f'{len(users)} пользователей, 24 заказа'
        ))

    # ── Clear ──────────────────────────────────────────────
    def _clear(self):
        self.stdout.write('Очищаю данные…')
        Favorite.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        ProductImage.objects.all().delete()
        ProductAttribute.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write('  Готово.')

    # ── Images ─────────────────────────────────────────────
    def _collect_images(self):
        zapchast = Path(settings.BASE_DIR) / 'ZAPCHAST'
        if not zapchast.exists():
            self.stdout.write(self.style.WARNING('Директория ZAPCHAST не найдена'))
            return []
        exts = {'.jpg','.jpeg','.png','.webp','.gif'}
        return [p for p in zapchast.iterdir() if p.suffix.lower() in exts]

    def _copy_image(self, src: Path) -> str:
        """Копирует файл в media/products/ и возвращает относительный путь."""
        dest_dir = Path(settings.MEDIA_ROOT) / 'products'
        dest_dir.mkdir(parents=True, exist_ok=True)
        # уникальное имя: случайный префикс + оригинальное имя
        dest_name = f'{random.randint(10000,99999)}_{src.name}'
        dest = dest_dir / dest_name
        shutil.copy2(src, dest)
        return f'products/{dest_name}'

    # ── Categories ─────────────────────────────────────────
    def _seed_categories(self):
        self.stdout.write('Создаю категории…')
        cats = {}
        for parent_name, children in CATEGORY_TREE.items():
            parent, _ = Category.objects.get_or_create(
                slug=_unique_slug(_slug(parent_name), Category),
                defaults={'name': parent_name},
            )
            cats[parent_name] = parent
            for child_name in children:
                child, _ = Category.objects.get_or_create(
                    slug=_unique_slug(_slug(child_name), Category),
                    defaults={'name': child_name, 'parent': parent},
                )
                cats[child_name] = child
        self.stdout.write(f'  {len(cats)} категорий')
        return cats

    # ── Products ───────────────────────────────────────────
    def _seed_products(self, categories, images):
        self.stdout.write('Создаю товары…')
        products = []
        used_skus = set(Product.objects.values_list('sku', flat=True))

        for i, (name, cat_name, attrs) in enumerate(PRODUCTS):
            cat = categories.get(cat_name)
            if not cat:
                continue

            brand = random.choice(BRANDS)
            price = Decimal(random.choice([
                random.randint(300, 2000),
                random.randint(2000, 8000),
                random.randint(8000, 35000),
            ]))
            stock = random.randint(0, 50)

            sku = f'{brand[:3].upper()}-{random.randint(10000,99999)}'
            while sku in used_skus:
                sku = f'{brand[:3].upper()}-{random.randint(10000,99999)}'
            used_skus.add(sku)

            base = _slug(f'{brand} {name}')
            slug = _unique_slug(base, Product)

            product = Product.objects.create(
                category=cat,
                name=name,
                slug=slug,
                sku=sku,
                brand=brand,
                price=price,
                stock=stock,
                is_available=stock > 0 or random.random() > 0.15,
                description=self._make_description(name, brand),
            )

            # Attributes
            for key, value, unit in attrs:
                ProductAttribute.objects.create(
                    product=product, key=key, value=value, unit=unit)

            # Images (1–3 random)
            if images:
                chosen = random.sample(images, min(random.randint(1, 3), len(images)))
                for j, img_path in enumerate(chosen):
                    rel = self._copy_image(img_path)
                    ProductImage.objects.create(
                        product=product,
                        image=rel,
                        is_main=(j == 0),
                        order=j,
                    )

            products.append(product)

        self.stdout.write(f'  {len(products)} товаров')
        return products

    def _make_description(self, name, brand):
        templates = [
            f'{name} от производителя {brand}. Оригинальное качество, соответствует заводским стандартам. Гарантия 12 месяцев.',
            f'Запчасть {name} ({brand}) — надёжное решение для вашего автомобиля. Совместима с широким рядом моделей.',
            f'{brand} {name} изготовлена из высококачественных материалов. Прошла контроль качества на заводе-изготовителе.',
        ]
        return random.choice(templates)

    # ── Admin ──────────────────────────────────────────────
    def _seed_admin(self):
        username = 'Hikmatullo'
        email    = 'abdunazarovhikmatullo2@gmail.com'
        password = '2008_8002'
        if User.objects.filter(username=username).exists():
            self.stdout.write(f'  Администратор «{username}» уже существует — пропускаю.')
            return
        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'  Администратор «{username}» создан (пароль: {password})'))

    # ── Users ──────────────────────────────────────────────
    def _seed_users(self):
        self.stdout.write('Создаю пользователей…')
        users = []
        for i in range(20):
            first = random.choice(FIRST_NAMES)
            last  = random.choice(LAST_NAMES)
            username = f'{_slug(first)}.{_slug(last)}{random.randint(1,99)}'
            email    = f'{username}@example.com'
            phone    = f'+7{random.randint(9000000000,9999999999)}'

            if User.objects.filter(username=username).exists():
                username += str(random.randint(100, 999))

            user = User.objects.create_user(
                username=username,
                email=email,
                password='test1234',
                first_name=first,
                last_name=last,
            )
            user.phone = phone
            user.save()
            users.append(user)

        self.stdout.write(f'  {len(users)} пользователей (пароль: test1234)')
        return users

    # ── Orders ─────────────────────────────────────────────
    def _seed_orders(self, users, products):
        self.stdout.write('Создаю заказы…')
        statuses = ['pending','confirmed','in_progress','ready','completed','cancelled']
        weights  = [0.30, 0.20, 0.20, 0.10, 0.15, 0.05]

        for _ in range(24):
            user   = random.choice(users)
            status = random.choices(statuses, weights=weights)[0]
            phone  = getattr(user, 'phone', '') or f'+7{random.randint(9000000000,9999999999)}'
            order  = Order.objects.create(
                user=user,
                status=status,
                phone=phone,
                comment=random.choice(['', '', '', 'Позвоните перед доставкой', 'Самовывоз']),
            )
            items = random.sample(products, random.randint(1, 5))
            for product in items:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=random.randint(1, 4),
                    price=product.price,
                )

        self.stdout.write('  24 заказа')

    # ── Favorites ──────────────────────────────────────────
    def _seed_favorites(self, users, products):
        self.stdout.write('Создаю избранное…')
        count = 0
        for user in random.sample(users, min(14, len(users))):
            favs = random.sample(products, random.randint(3, 8))
            for product in favs:
                Favorite.objects.get_or_create(user=user, product=product)
                count += 1
        self.stdout.write(f'  {count} записей избранного')
