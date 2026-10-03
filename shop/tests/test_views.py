from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from shop.forms import PurchaseForm
from shop.models import Product
from shop import views


class PurchaseFormUnitTests(SimpleTestCase):
    def setUp(self):
        self.product = SimpleNamespace(stock=1, purchase=Mock(return_value='order'))
        self.data = {'person': 'Ирина', 'address': 'Москва, ул. Мира, 1'}

    def test_valid_form_delegates_save_to_product(self):
        form = PurchaseForm(data=self.data, product=self.product)

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save(), 'order')
        self.product.purchase.assert_called_once_with(**self.data)

    def test_form_rejects_when_no_stock(self):
        self.product.stock = 0
        form = PurchaseForm(data=self.data, product=self.product)

        self.assertFalse(form.is_valid())
        self.assertIn('Товар закончился. Покупка невозможна.', form.non_field_errors())
        self.product.purchase.assert_not_called()

    def test_form_exposes_bootstrap_widgets(self):
        form = PurchaseForm(product=self.product)

        self.assertEqual(form.fields['person'].widget.attrs['class'], 'form-control')
        self.assertEqual(form.fields['address'].widget.attrs['class'], 'form-control')


class ViewUnitTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch('shop.views.render')
    @patch('shop.views.Product.objects')
    def test_index_filters_active_products_and_sorts(self, manager, render):
        request = self.factory.get('/')
        products = object()
        manager.filter.return_value.order_by.return_value = products

        response = views.index(request)

        manager.filter.assert_called_once_with(is_active=True)
        manager.filter.return_value.order_by.assert_called_once_with('name')
        render.assert_called_once_with(request, 'shop/index.html', {'products': products})
        self.assertEqual(response, render.return_value)

    @patch('shop.views.render')
    @patch('shop.views.PurchaseForm')
    @patch('shop.views.get_object_or_404')
    def test_buy_get_builds_form_without_saving(self, get_product, form_class, render):
        request = self.factory.get('/buy/5/')
        product = get_product.return_value

        response = views.buy(request, 5)

        get_product.assert_called_once_with(Product, pk=5, is_active=True)
        form_class.assert_called_once_with(None, product=product)
        form_class.return_value.save.assert_not_called()
        render.assert_called_once_with(request, 'shop/purchase_form.html', {
            'form': form_class.return_value, 'product': product,
        })
        self.assertEqual(response, render.return_value)

    @patch('shop.views.redirect')
    @patch('shop.views.PurchaseForm')
    @patch('shop.views.get_object_or_404')
    def test_buy_valid_post_saves_and_redirects(self, get_product, form_class, redirect):
        request = self.factory.post('/buy/5/', {'person': 'Ирина'})
        form_class.return_value.is_valid.return_value = True

        response = views.buy(request, 5)

        form_class.assert_called_once_with(request.POST, product=get_product.return_value)
        form_class.return_value.save.assert_called_once_with()
        redirect.assert_called_once_with('index')
        self.assertEqual(response, redirect.return_value)

    @patch('shop.views.render')
    @patch('shop.views.PurchaseForm')
    @patch('shop.views.get_object_or_404')
    def test_buy_invalid_post_renders_bound_form(self, get_product, form_class, render):
        request = self.factory.post('/buy/5/', {'person': ''})
        form_class.return_value.is_valid.return_value = False

        response = views.buy(request, 5)

        form_class.return_value.save.assert_not_called()
        render.assert_called_once_with(request, 'shop/purchase_form.html', {
            'form': form_class.return_value, 'product': get_product.return_value,
        })
        self.assertEqual(response, render.return_value)
