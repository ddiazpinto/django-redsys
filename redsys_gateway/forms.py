from django import forms


class GatewayForm(forms.Form):
    Ds_Signature = forms.CharField(max_length=256)
    Ds_MerchantParameters = forms.CharField(max_length=2048)
    Ds_SignatureVersion = forms.CharField(max_length=256)
