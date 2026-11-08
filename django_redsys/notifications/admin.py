from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['order', 'response_code', 'authorized', 'amount', 'currency', 'environment', 'count', 'received_at']
    list_filter = ['authorized', 'environment', 'transaction_type', 'processed_pay_method']
    search_fields = ['order', 'authorization_code']
    date_hierarchy = 'received_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
