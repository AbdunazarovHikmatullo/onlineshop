from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from cart.models import Order
from cart.email import send_status_email
from cart.telegram import send_status_update
from .forms import CategoryForm, ProductAttributeFormSet, ProductForm
from .models import Category, Favorite, Product, ProductImage


# ── Public views ──────────────────────────────────────────

def index(request):
    latest_products = (
        Product.objects
        .filter(is_available=True)
        .select_related('category')
        .prefetch_related('images')
        .order_by('-created_at')[:8]
    )
    categories = Category.objects.filter(parent=None)[:6]
    return render(request, 'main/index.html', {
        'latest_products': latest_products,
        'categories': categories,
    })


def catalog(request):
    products = (
        Product.objects
        .filter(is_available=True)
        .select_related('category')
        .prefetch_related('images')
    )
    categories = Category.objects.filter(parent=None).prefetch_related('children')
    brands = (
        Product.objects
        .filter(is_available=True)
        .exclude(brand='')
        .values_list('brand', flat=True)
        .distinct()
        .order_by('brand')
    )

    category_slug  = request.GET.get('category', '')
    selected_brands = request.GET.getlist('brand')
    price_min      = request.GET.get('price_min', '')
    price_max      = request.GET.get('price_max', '')
    sort           = request.GET.get('sort', '-created_at')
    q              = request.GET.get('q', '').strip()

    selected_category = None
    if category_slug:
        try:
            selected_category = Category.objects.get(slug=category_slug)
            descendants = list(selected_category.children.values_list('id', flat=True))
            descendants.append(selected_category.id)
            products = products.filter(category_id__in=descendants)
        except Category.DoesNotExist:
            pass

    if selected_brands:
        products = products.filter(brand__in=selected_brands)
    if price_min:
        products = products.filter(price__gte=price_min)
    if price_max:
        products = products.filter(price__lte=price_max)
    if q:
        products = (
            products.filter(name__icontains=q) |
            products.filter(sku__icontains=q) |
            products.filter(brand__icontains=q)
        ).distinct()

    allowed_sorts = {'price', '-price', 'name', '-created_at'}
    if sort not in allowed_sorts:
        sort = '-created_at'
    products = products.order_by(sort)

    paginator = Paginator(products, 24)
    page_obj = paginator.get_page(request.GET.get('page'))

    params = request.GET.copy()
    params.pop('page', None)
    filter_qs = params.urlencode()

    return render(request, 'product/catalog.html', {
        'products': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_range': paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1),
        'filter_qs': filter_qs,
        'categories': categories,
        'brands': brands,
        'selected_category': selected_category,
        'selected_brands': selected_brands,
        'price_min': price_min,
        'price_max': price_max,
        'sort': sort,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_available=True)
    related = (
        Product.objects
        .filter(category=product.category, is_available=True)
        .exclude(pk=product.pk)
        .prefetch_related('images')[:4]
    )
    return render(request, 'product/detail.html', {
        'product': product,
        'related': related,
    })


# ── Favorites ─────────────────────────────────────────────

@login_required
def favorites(request):
    products = (
        Product.objects
        .filter(favorited_by__user=request.user)
        .prefetch_related('images')
        .order_by('-favorited_by__created_at')
    )
    return render(request, 'product/favorites.html', {'products': products})


@login_required
@require_POST
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    fav, created = Favorite.objects.get_or_create(user=request.user, product=product)
    if not created:
        fav.delete()
        is_fav = False
    else:
        is_fav = True
    count = Favorite.objects.filter(user=request.user).count()
    return JsonResponse({'success': True, 'is_favorited': is_fav, 'count': count})


# ── Superuser-only CRUD ───────────────────────────────────

_TRANSLIT = {
    'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
    'з':'z','и':'i','й':'j','к':'k','л':'l','м':'m','н':'n','о':'o',
    'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts',
    'ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
}

def _make_slug(name):
    from django.utils.text import slugify
    t = ''.join(_TRANSLIT.get(c, c) for c in name.lower())
    return slugify(t) or slugify(name)


def _unique_slug(base, exclude_pk=None):
    slug, n = base, 1
    qs = Product.objects.all()
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=slug).exists():
        slug = f'{base}-{n}'
        n += 1
    return slug


def _save_images(product, files, main_idx):
    start = product.images.count()
    for i, f in enumerate(files):
        ProductImage.objects.create(
            product=product,
            image=f,
            is_main=(i == main_idx),
            order=start + i,
        )


def _superuser_required(request):
    if not request.user.is_authenticated:
        from django.conf import settings
        return redirect(f'{settings.LOGIN_URL}?next={request.path}')
    if not request.user.is_superuser:
        raise PermissionDenied
    return None


@login_required
def product_add(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    if request.method == 'POST':
        form    = ProductForm(request.POST)
        attr_fs = ProductAttributeFormSet(request.POST, prefix='attrs')
        if form.is_valid() and attr_fs.is_valid():
            product = form.save(commit=False)
            if not product.slug:
                product.slug = _unique_slug(_make_slug(product.name))
            product.save()
            # Images
            files = request.FILES.getlist('images')
            try:
                main_idx = int(request.POST.get('main_image', 0))
            except (ValueError, TypeError):
                main_idx = 0
            _save_images(product, files, main_idx)
            attr_fs.instance = product
            attr_fs.save()
            return redirect('product:detail', slug=product.slug)
    else:
        form    = ProductForm()
        attr_fs = ProductAttributeFormSet(prefix='attrs')
    return render(request, 'product/product_form.html', {
        'form': form, 'attr_fs': attr_fs,
        'action': 'Добавить товар',
    })


@login_required
def product_edit(request, slug):
    if not request.user.is_superuser:
        raise PermissionDenied
    product = get_object_or_404(Product, slug=slug)
    if request.method == 'POST':
        form    = ProductForm(request.POST, instance=product)
        attr_fs = ProductAttributeFormSet(request.POST, instance=product, prefix='attrs')
        if form.is_valid() and attr_fs.is_valid():
            product = form.save(commit=False)
            if not product.slug:
                product.slug = _unique_slug(_make_slug(product.name), exclude_pk=product.pk)
            product.save()
            attr_fs.save()
            # Delete images marked for removal
            for img_id in request.POST.getlist('delete_image'):
                ProductImage.objects.filter(pk=img_id, product=product).delete()
            # Set main from existing
            main_existing = request.POST.get('main_existing')
            if main_existing:
                product.images.update(is_main=False)
                product.images.filter(pk=main_existing).update(is_main=True)
            # New uploaded images
            files = request.FILES.getlist('images')
            if files:
                if not main_existing:
                    try:
                        main_idx = int(request.POST.get('main_image', 0))
                    except (ValueError, TypeError):
                        main_idx = 0
                else:
                    main_idx = -1
                _save_images(product, files, main_idx)
            return redirect('product:detail', slug=product.slug)
    else:
        form    = ProductForm(instance=product)
        attr_fs = ProductAttributeFormSet(instance=product, prefix='attrs')
    return render(request, 'product/product_form.html', {
        'form': form, 'attr_fs': attr_fs,
        'product': product, 'action': 'Редактировать товар',
        'existing_images': product.images.all(),
    })


@login_required
def product_delete(request, slug):
    if not request.user.is_superuser:
        raise PermissionDenied
    product = get_object_or_404(Product, slug=slug)
    if request.method == 'POST':
        product.delete()
        return redirect('product:catalog')
    return render(request, 'product/product_confirm_delete.html', {'product': product})


# ── Dashboard ─────────────────────────────────────────────

@login_required
def dashboard(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    orders_by_status = dict(
        Order.objects.values_list('status').annotate(count=Count('id'))
    )
    recent_orders = (
        Order.objects
        .select_related('user')
        .prefetch_related('items__product')
        .order_by('-created_at')[:15]
    )

    cat_form = CategoryForm()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_category':
            cat_form = CategoryForm(request.POST)
            if cat_form.is_valid():
                cat_form.save()
                return redirect(reverse('product:dashboard') + '#categories')
        elif action == 'edit_category':
            cat_id = request.POST.get('cat_id')
            cat = Category.objects.filter(pk=cat_id).first()
            if cat:
                edit_form = CategoryForm(request.POST, instance=cat)
                if edit_form.is_valid():
                    edit_form.save()
            return redirect(reverse('product:dashboard') + '#categories')
        elif action == 'delete_category':
            cat_id = request.POST.get('cat_id')
            Category.objects.filter(pk=cat_id).delete()
            return redirect(reverse('product:dashboard') + '#categories')
        else:
            order_id = request.POST.get('order_id')
            new_status = request.POST.get('status')
            allowed = {s[0] for s in Order.STATUS_CHOICES}
            if order_id and new_status in allowed:
                Order.objects.filter(pk=order_id).update(status=new_status)
                order = Order.objects.select_related('user').filter(pk=order_id).first()
                if order:
                    send_status_update(order)
                    send_status_email(order)
            return redirect('product:dashboard')

    all_categories = Category.objects.select_related('parent').order_by('name')

    return render(request, 'dashboard/index.html', {
        'total_products': Product.objects.count(),
        'available':      Product.objects.filter(is_available=True).count(),
        'out_of_stock':   Product.objects.filter(stock=0, is_available=True).count(),
        'total_orders':   Order.objects.count(),
        'pending_orders': orders_by_status.get('pending', 0),
        'orders_by_status': orders_by_status,
        'recent_orders':  recent_orders,
        'status_choices': Order.STATUS_CHOICES,
        'cat_form':       cat_form,
        'all_categories': all_categories,
    })
