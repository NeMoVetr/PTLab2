from django import forms

from .models import Purchase


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['person', 'address']
        labels = {'person': 'Ваше имя', 'address': 'Адрес доставки'}
        widgets = {
            'person': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Как к вам обращаться?',
                'autocomplete': 'name',
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Город, улица, дом',
                'autocomplete': 'street-address',
            }),
        }

    def __init__(self, *args, product, **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product

    def clean(self):
        cleaned_data = super().clean()
        if self.product.stock == 0:
            raise forms.ValidationError('Товар закончился. Покупка невозможна.')
        return cleaned_data

    def save(self):
        return self.product.purchase(
            person=self.cleaned_data['person'],
            address=self.cleaned_data['address'],
        )
