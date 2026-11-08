from django.urls import path

from . import views

app_name = 'redsys_gateway'
urlpatterns = [
    path('notification/', views.NotificationView.as_view(), name='notification'),
    path('ok/', views.ResultView.as_view(template_name='redsys_gateway/ok.html'), name='ok'),
    path('ko/', views.ResultView.as_view(template_name='redsys_gateway/ko.html'), name='ko'),
]
