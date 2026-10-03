from importlib import import_module

from django.apps import apps
from django.db import connection
from django.test import TestCase

from shop.models import Product


class CatalogDataTests(TestCase):
    def test_luxury_seed_is_repeatable_and_does_not_restock(self):
        seed = import_module('shop.migrations.0003_luxury_products').add_luxury_products
        with connection.schema_editor(atomic=False) as editor:
            seed(apps, editor)
            watch = Product.objects.get(name='Часы Seamaster', brand='Omega')
            watch.stock = 0
            watch.save()
            count = Product.objects.count()
            seed(apps, editor)
        watch.refresh_from_db()
        self.assertEqual(watch.stock, 0)
        self.assertEqual(Product.objects.count(), count)
        self.assertTrue(Product.objects.filter(brand='Cartier').exists())
        self.assertEqual(Product.objects.get(brand='Montblanc').stock, 0)

    def test_patek_catalog_preserves_old_items_but_deactivates_them(self):
        Product.objects.create(name='Старые часы', brand='Omega', price=100, stock=2)
        replace_catalog = import_module('shop.migrations.0004_patek_philippe_catalog').replace_catalog
        with connection.schema_editor(atomic=False) as editor:
            replace_catalog(apps, editor)
        old_product = Product.objects.get(name='Старые часы')
        self.assertFalse(old_product.is_active)
        self.assertEqual(old_product.stock, 2)
        self.assertEqual(
            set(Product.objects.filter(is_active=True).values_list('name', flat=True)),
            {'Calatrava', 'Nautilus', 'Aquanaut', 'Complications'},
        )
