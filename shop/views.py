from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import PurchaseForm
from .models import Product


@require_http_methods(['GET'])
def index(request):
    products = Product.objects.filter(is_active=True).order_by('name')
    return render(request, 'shop/index.html', {'products': products})


@require_http_methods(['GET', 'POST'])
def buy(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    form = PurchaseForm(request.POST if request.method == 'POST' else None,
                        product=product)
    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
        except ValidationError as error:
            form.add_error(None, error)
            product.refresh_from_db()
        else:
            return redirect('index')
    return render(request, 'shop/purchase_form.html', {
        'form': form, 'product': product,
    })

