from .models import Category


def product_categories(request):
    return {
        'categories': Category.objects.filter(parent__isnull=True).order_by('name')
    }
