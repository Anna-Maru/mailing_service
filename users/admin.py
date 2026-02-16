from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Административная панель для пользователей"""

    list_display = (
        'username', 'email', 'role', 'is_email_verified',
        'is_blocked', 'is_active', 'date_joined'
    )
    list_filter = ('role', 'is_email_verified', 'is_blocked', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('role', 'phone', 'avatar', 'is_email_verified',
                       'email_verification_token', 'is_blocked', 'blocked_reason')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительная информация', {
            'fields': ('email', 'role', 'phone')
        }),
    )
