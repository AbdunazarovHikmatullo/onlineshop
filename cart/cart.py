from product.models import Product

SESSION_KEY = 'cart'


class Cart:
    def __init__(self, request):
        self.session = request.session
        self._data = dict(self.session.get(SESSION_KEY, {}))

    def _save(self):
        self.session[SESSION_KEY] = self._data
        self.session.modified = True

    def add(self, product_id, quantity=1):
        key = str(product_id)
        self._data[key] = self._data.get(key, 0) + quantity
        self._save()

    def update(self, product_id, quantity):
        key = str(product_id)
        if quantity <= 0:
            self._data.pop(key, None)
        else:
            self._data[key] = quantity
        self._save()

    def remove(self, product_id):
        self._data.pop(str(product_id), None)
        self._save()

    def clear(self):
        self._data = {}
        self._save()

    def count(self):
        return sum(self._data.values())

    def get_items(self):
        if not self._data:
            return []
        ids = [int(k) for k in self._data]
        products = {
            p.pk: p
            for p in Product.objects.filter(pk__in=ids).prefetch_related('images')
        }
        items = []
        for pid, qty in self._data.items():
            product = products.get(int(pid))
            if product:
                items.append({
                    'product':  product,
                    'quantity': qty,
                    'subtotal': product.price * qty,
                })
        return items

    def total(self):
        return sum(item['subtotal'] for item in self.get_items())
