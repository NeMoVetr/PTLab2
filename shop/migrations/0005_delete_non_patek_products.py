from django.db import migrations


def delete_non_patek_products(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    Product.objects.using(schema_editor.connection.alias).exclude(
        brand='Patek Philippe',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('shop', '0004_patek_philippe_catalog')]

    operations = [
        migrations.RunPython(delete_non_patek_products, migrations.RunPython.noop),
    ]
