from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from django.core.exceptions import ValidationError

from shop.models import Product, Purchase


class ProductPurchaseUnitTests(TestCase):
    @patch('shop.models.Product.objects')
    @patch('shop.models.Purchase')
    @patch('shop.models.transaction.atomic')
    def test_purchase_creates_order_and_decrements_stock(self, atomic, purchase_model, manager):
        product = SimpleNamespace(pk=7, stock=3, is_active=True)
        locked_product = SimpleNamespace(pk=7, stock=3, is_active=True)
        manager.select_for_update.return_value.get.return_value = locked_product
        order = purchase_model.return_value
        order.product = locked_product

        result = Product.purchase(product, person='Ирина', address='Москва')

        purchase_model.assert_called_once_with(
            product=locked_product, person='Ирина', address='Москва'
        )
        order.full_clean.assert_called_once_with()
        order.save.assert_called_once_with()
        manager.filter.assert_called_once_with(pk=7)
        manager.filter.return_value.update.assert_called_once()
        atomic.assert_called_once_with()
        self.assertEqual(product.stock, 2)
        self.assertEqual(result, order)

    @patch('shop.models.Product.objects')
    @patch('shop.models.Purchase')
    @patch('shop.models.transaction.atomic')
    def test_purchase_rejects_inactive_product(self, atomic, purchase_model, manager):
        manager.select_for_update.return_value.get.return_value = SimpleNamespace(
            pk=7, stock=2, is_active=False
        )

        with self.assertRaisesRegex(ValidationError, r'Эта модель больше не продаётся\.'):
            Product.purchase(SimpleNamespace(pk=7), person='Ирина', address='Москва')

        purchase_model.assert_not_called()
        manager.filter.assert_not_called()
        atomic.assert_called_once_with()

    @patch('shop.models.Product.objects')
    @patch('shop.models.Purchase')
    @patch('shop.models.transaction.atomic')
    def test_purchase_rejects_empty_stock(self, atomic, purchase_model, manager):
        manager.select_for_update.return_value.get.return_value = SimpleNamespace(
            pk=7, stock=0, is_active=True
        )

        with self.assertRaisesRegex(ValidationError, r'Товар закончился\. Покупка невозможна\.'):
            Product.purchase(SimpleNamespace(pk=7), person='Ирина', address='Москва')

        purchase_model.assert_not_called()
        manager.filter.assert_not_called()

    def test_model_string_representations(self):
        product = Product(name='Calatrava')
        self.assertEqual(str(product), 'Calatrava')

        purchase = Purchase(product_id=1, person='Ирина', address='Москва')
        purchase._state.fields_cache['product'] = product
        self.assertEqual(str(purchase), 'Calatrava — Ирина')
