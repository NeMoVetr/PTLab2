from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F

# Create your models here.
class Product(models.Model):
    name = models.CharField(max_length=200)
    price = models.PositiveIntegerField()
    brand = models.CharField('Марка', max_length=100, blank=True)
    description = models.TextField('Описание', blank=True)
    stock = models.PositiveIntegerField('Остаток', default=0)

    def __str__(self):
        return self.name

    def purchase(self, person, address):
        """Создать покупку и списать одну единицу в общей транзакции."""
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=self.pk)
            if product.stock == 0:
                raise ValidationError('Товар закончился. Покупка невозможна.')
            purchase = Purchase(product=product, person=person, address=address)
            purchase.full_clean()
            purchase.save()
            Product.objects.filter(pk=product.pk).update(stock=F('stock') - 1)
        self.stock = product.stock - 1
        return purchase

class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    person = models.CharField(max_length=200)
    address = models.CharField(max_length=200)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.product} — {self.person}'
