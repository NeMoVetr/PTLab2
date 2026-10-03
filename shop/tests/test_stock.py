from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from shop.admin import ProductAdmin, PurchaseAdmin
from shop.forms import PurchaseForm
from shop.models import Product, Purchase
from django.contrib.admin.sites import AdminSite


class StockTests(TestCase):
    def setUp(self):
        Product.objects.all().delete()
        self.product = Product.objects.create(name='Часы', brand='Patek Philippe', price=650000, stock=2)
        self.data = {'person': 'Иван', 'address': 'Москва, ул. Мира, 1'}

    def test_purchase_decrements_stock_and_records_order(self):
        purchase = self.product.purchase(**self.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertEqual(purchase.product, self.product)
        self.assertEqual(purchase.person, self.data['person'])
        self.assertEqual(purchase.address, self.data['address'])
        self.assertIsNotNone(purchase.date)

    def test_last_item_and_repeated_purchase(self):
        self.product.stock = 1
        self.product.save()
        self.product.purchase(**self.data)
        with self.assertRaises(ValidationError):
            self.product.purchase(**self.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        self.assertEqual(Purchase.objects.count(), 1)

    def test_stale_product_cannot_buy_sold_item(self):
        Product.objects.filter(pk=self.product.pk).update(stock=0)
        with self.assertRaises(ValidationError):
            self.product.purchase(**self.data)
        self.assertFalse(Purchase.objects.exists())

    def test_invalid_customer_does_not_change_stock(self):
        with self.assertRaises(ValidationError):
            self.product.purchase(person='', address='')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.assertFalse(Purchase.objects.exists())

    def test_stock_update_failure_rolls_back_purchase(self):
        with patch('django.db.models.query.QuerySet.update', side_effect=IntegrityError):
            with self.assertRaises(IntegrityError):
                self.product.purchase(**self.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.assertFalse(Purchase.objects.exists())

    def test_database_rejects_negative_stock(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=self.product.pk).update(stock=-1)

    def test_model_validation_and_display_names(self):
        self.assertEqual(str(self.product), 'Часы')
        purchase = self.product.purchase(**self.data)
        self.assertEqual(str(purchase), 'Часы — Иван')
        self.product.stock = -1
        with self.assertRaises(ValidationError):
            self.product.full_clean()

    def test_form_accepts_valid_data(self):
        form = PurchaseForm(data=self.data, product=self.product)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().product, self.product)
        self.assertEqual(form.fields['person'].widget.attrs['class'], 'form-control')

    def test_form_rejects_missing_whitespace_and_long_values(self):
        for data in ({}, {'person': '   ', 'address': '   '},
                     {'person': 'x' * 201, 'address': 'x' * 201}):
            with self.subTest(data=data):
                form = PurchaseForm(data=data, product=self.product)
                self.assertFalse(form.is_valid())
        self.assertFalse(Purchase.objects.exists())

    def test_form_rejects_out_of_stock(self):
        self.product.stock = 0
        form = PurchaseForm(data=self.data, product=self.product)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.non_field_errors())

    def test_catalog_shows_luxury_information(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Patek Philippe')
        self.assertContains(response, '650000')
        self.assertContains(response, 'В наличии: 2')
        self.assertContains(response, 'bootstrap@5.3.8')
        self.assertNotContains(response, 'style.css')

    def test_empty_catalog(self):
        Product.objects.all().delete()
        self.assertContains(self.client.get(reverse('index')), 'Пока нет товаров')

    def test_catalog_disables_sold_product(self):
        self.product.stock = 0
        self.product.save()
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'Нет в наличии')
        self.assertNotContains(response, f'href="{reverse("buy", args=[self.product.pk])}"')

    def test_get_form_does_not_buy(self):
        response = self.client.get(reverse('buy', args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="person"')
        self.assertFalse(Purchase.objects.exists())

    def test_post_purchase_redirect_and_refresh(self):
        response = self.client.post(reverse('buy', args=[self.product.pk]), self.data, follow=True)
        self.assertRedirects(response, reverse('index'))
        self.assertNotContains(response, 'Спасибо за покупку')
        self.client.get(reverse('index'))
        self.assertEqual(Purchase.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_invalid_post_preserves_values_and_stock(self):
        response = self.client.post(reverse('buy', args=[self.product.pk]), {'person': 'Иван'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Иван"')
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(Purchase.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)

    def test_sold_product_get_and_post(self):
        self.product.stock = 0
        self.product.save()
        url = reverse('buy', args=[self.product.pk])
        for response in (self.client.get(url), self.client.post(url, self.data)):
            self.assertContains(response, 'Покупка невозможна')
            self.assertContains(response, 'disabled')
        self.assertFalse(Purchase.objects.exists())

    def test_race_after_form_validation_is_reported(self):
        url = reverse('buy', args=[self.product.pk])
        original_save = PurchaseForm.save

        def sold_before_save(form):
            Product.objects.filter(pk=form.product.pk).update(stock=0)
            return original_save(form)

        with patch.object(PurchaseForm, 'save', sold_before_save):
            response = self.client.post(url, self.data)
        self.assertContains(response, 'Покупка невозможна')
        self.assertEqual(response.context['product'].stock, 0)
        self.assertFalse(Purchase.objects.exists())

    def test_unknown_product_returns_404(self):
        for method in (self.client.get, self.client.post):
            self.assertEqual(method(reverse('buy', args=[999999])).status_code, 404)

    def test_inactive_product_is_hidden_and_cannot_be_bought(self):
        self.product.name = 'OLD-WATCH-123'
        self.product.is_active = False
        self.product.save()
        self.assertNotContains(self.client.get(reverse('index')), self.product.name)
        self.assertEqual(self.client.get(reverse('buy', args=[self.product.pk])).status_code, 404)
        self.assertFalse(Purchase.objects.exists())

    def test_post_cannot_replace_url_product(self):
        other = Product.objects.create(name='Сумка', price=500000, stock=5)
        self.client.post(reverse('buy', args=[self.product.pk]), {**self.data, 'product': other.pk})
        self.assertEqual(Purchase.objects.get().product, self.product)
        other.refresh_from_db()
        self.assertEqual(other.stock, 5)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('buy', args=[self.product.pk]), self.data).status_code, 403)
        self.assertFalse(Purchase.objects.exists())

    def test_unsupported_methods(self):
        self.assertEqual(self.client.post(reverse('index')).status_code, 405)
        self.assertEqual(self.client.put(reverse('buy', args=[self.product.pk])).status_code, 405)

    def test_customer_name_is_escaped(self):
        response = self.client.post(
            reverse('buy', args=[self.product.pk]),
            {'person': '<script>alert(1)</script>', 'address': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;')
        self.assertFalse(Purchase.objects.exists())

    def test_admin_prevents_direct_orders_and_deletion(self):
        admin = PurchaseAdmin(Purchase, AdminSite())
        self.assertFalse(admin.has_add_permission(None))
        self.assertFalse(admin.has_delete_permission(None))
        self.assertIn('stock', ProductAdmin.list_display)


class ConcurrentPurchaseTests(TransactionTestCase):
    def test_two_buyers_cannot_buy_last_item_twice(self):
        self.assertEqual(connection.vendor, 'postgresql')
        product = Product.objects.create(name='Браслет', price=900000, stock=1)
        barrier = Barrier(2)

        def buy_item():
            close_old_connections()
            try:
                item = Product.objects.get(pk=product.pk)
                barrier.wait(timeout=10)
                try:
                    item.purchase(person='Покупатель', address='Москва')
                    return True
                except ValidationError:
                    return False
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: buy_item(), range(2)))
        self.assertCountEqual(results, [True, False])
        product.refresh_from_db()
        self.assertEqual(product.stock, 0)
        self.assertEqual(Purchase.objects.filter(product=product).count(), 1)
