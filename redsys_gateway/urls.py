from django.conf.urls import url
from . import views


app_name = 'redsys_gateway'
urlpatterns = [
    url(r'^redirect/$', views.redirect_view, name='redirect'),
    url(r'^response/$', views.response_view, name='response'),
    url(r'^accepted/$', views.accepted_view, name='accepted'),
    url(r'^rejected/$', views.rejected_view, name='rejected'),
]