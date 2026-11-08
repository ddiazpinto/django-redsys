import pytest
from django.conf import settings
from redsys.crypto import get_signer
from redsys.models import decode_merchant_parameters
from redsys.request import MERCHANT_PARAMETERS


def signed(parameters, secret_key=None, version='HMAC_SHA512_V2'):
    """The three fields RedSys posts for ``parameters``, signed as RedSys signs them."""
    signer = get_signer(secret_key or settings.REDSYS_CLIENT['secret_key'], version)
    merchant_parameters = signer.encode_parameters(parameters)
    return {
        'Ds_SignatureVersion': version,
        'Ds_MerchantParameters': merchant_parameters.decode(),
        'Ds_Signature': signer.sign(parameters['Ds_Order'], merchant_parameters).decode(),
    }


def decoded(fields):
    return decode_merchant_parameters(fields[MERCHANT_PARAMETERS].encode())


@pytest.fixture
def notification():
    return {
        'Ds_Order': '1234abcd',
        'Ds_Amount': '1056',
        'Ds_Currency': '978',
        'Ds_Response': '0000',
        'Ds_MerchantCode': '999008881',
        'Ds_Terminal': '1',
        'Ds_TransactionType': '0',
        'Ds_MerchantData': 'cart=7',
    }
