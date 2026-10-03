from django.db import migrations


def add_luxury_products(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    products = [
        ('Часы Seamaster', 'Omega', 'Швейцарские механические часы в стальном корпусе.', 650000, 3),
        ('Сумка Lady Dior', 'Dior', 'Кожаная сумка с фирменной стёжкой Cannage.', 580000, 2),
        ('Браслет Love', 'Cartier', 'Браслет из жёлтого золота 750 пробы.', 920000, 1),
        ('Перьевая ручка Meisterstück', 'Montblanc', 'Перьевая ручка с золотым пером.', 125000, 0),
    ]
    for name, brand, description, price, stock in products:
        Product.objects.using(schema_editor.connection.alias).get_or_create(
            name=name, brand=brand,
            defaults={'description': description, 'price': price, 'stock': stock},
        )


class Migration(migrations.Migration):
    dependencies = [('shop', '0002_product_brand_product_description_product_stock')]
    operations = [migrations.RunPython(add_luxury_products, migrations.RunPython.noop)]
