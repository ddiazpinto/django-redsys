from django.urls import path

from . import views

app_name = 'django_redsys'
urlpatterns = [
    path('notification/', views.NotificationView.as_view(), name='notification'),
    path('ok/', views.ResultView.as_view(template_name='django_redsys/ok.html'), name='ok'),
    path('ko/', views.ResultView.as_view(template_name='django_redsys/ko.html'), name='ko'),
]
