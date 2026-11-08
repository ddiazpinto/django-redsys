from decimal import Decimal

from django import forms
from django.urls import include, path
from redsys import transactions

from redsys_gateway.views import RedsysPaymentFormView, RedsysPaymentView


class PaymentView(RedsysPaymentView):
    def get_redsys_fields(self):
        return {'order': self.kwargs['order'], 'amount': Decimal('10.56'), 'merchant_data': 'cart=7'}


class PreauthorizationView(RedsysPaymentView):
    transaction_type = transactions.PREAUTHORIZATION

    def get_redsys_fields(self):
        return {'order': '1234abcd', 'amount': Decimal('1.00'), 'url_ok': 'https://shop.example/thanks'}


class MissingFieldsView(RedsysPaymentView):
    pass


class AmountForm(forms.Form):
    amount = forms.DecimalField(decimal_places=2)


class PaymentFormView(RedsysPaymentFormView):
    form_class = AmountForm
    template_name = 'pay-form.html'

    def get_redsys_fields(self):
        return {'order': '5678efgh', 'amount': self.form.cleaned_data['amount']}


urlpatterns = [
    path('pay/<str:order>/', PaymentView.as_view(), name='pay'),
    path('preauthorize/', PreauthorizationView.as_view(), name='preauthorize'),
    path('missing/', MissingFieldsView.as_view(), name='missing'),
    path('pay-form/', PaymentFormView.as_view(), name='pay-form'),
    path('redsys/', include('redsys_gateway.urls')),
]
