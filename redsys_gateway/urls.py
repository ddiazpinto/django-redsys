from __future__ import absolute_import, unicode_literals

from django.conf.urls import url
from django.views.generic import TemplateView

from .views import (response_view)


urlpatterns = [
    url(r'^response/$',
        response_view,
        name='redsys_gateway-response'),
    url(r'^accepted/$',
        TemplateView.as_view(template_name='redsys_gateway/transaction-accepted.html'),
        name='redsys_gateway-transaction-accepted'),
    url(r'^rejected/$',
        TemplateView.as_view(template_name='redsys_gateway/transaction-rejected.html'),
        name='redsys_gateway-transaction-rejected'),
]