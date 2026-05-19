from .models import Favorite


def favorites(request):
    if request.user.is_authenticated:
        ids = set(
            Favorite.objects.filter(user=request.user)
            .values_list('product_id', flat=True)
        )
        return {'fav_ids': ids, 'fav_count': len(ids)}
    return {'fav_ids': set(), 'fav_count': 0}
