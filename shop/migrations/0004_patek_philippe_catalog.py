from django.db import migrations, models


def replace_catalog(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    manager = Product.objects.using(schema_editor.connection.alias)

    # Keep retired products and their order history in the database, but remove
    # them from the storefront.
    manager.update(is_active=False)

    watches = [
        ('Calatrava', 'Классическая коллекция Patek Philippe. Демонстрационные данные.', 6400000, 2),
        ('Nautilus', 'Коллекция спортивных часов с узнаваемым восьмиугольным безелем. Демонстрационные данные.', 11200000, 1),
        ('Aquanaut', 'Коллекция с округлым восьмиугольным безелем и современным дизайном. Демонстрационные данные.', 9500000, 3),
        ('Complications', 'Механические часы с усложнениями: календарём, хронографом и другими функциями. Демонстрационные данные.', 17500000, 0),
    ]
    for name, description, price, stock in watches:
        product, created = manager.get_or_create(
            brand='Patek Philippe',
            name=name,
            defaults={
                'description': description,
                'price': price,
                'stock': stock,
                'is_active': True,
            },
        )
        if not created:
            manager.filter(pk=product.pk).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [('shop', '0003_luxury_products')]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Показывать в каталоге'),
        ),
        migrations.RunPython(replace_catalog, migrations.RunPython.noop),
    ]
