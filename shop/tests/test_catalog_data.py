from importlib import import_module

from django.apps import apps
from django.db import connection
from django.test import TestCase

from shop.models import Product


class CatalogDataTests(TestCase):
    def test_data_migration_adds_luxury_products_without_restocking(self):
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
