from django.contrib import admin
from .models import Client, Message, Mailing, MailingAttempt


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Административная панель для клиентов"""

    list_display = ('full_name', 'email', 'comment')
    search_fields = ('full_name', 'email')
    list_filter = ('full_name',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Административная панель для сообщений"""

    list_display = ('subject', 'created_at')
    search_fields = ('subject', 'body')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)


class MailingAttemptInline(admin.TabularInline):
    """Inline для отображения попыток рассылки"""

    model = MailingAttempt
    extra = 0
    readonly_fields = ('attempt_time', 'status', 'server_response', 'recipient_email')
    can_delete = False


@admin.register(Mailing)
class MailingAdmin(admin.ModelAdmin):
    """Административная панель для рассылок"""

    list_display = ('id', 'message', 'start_time', 'end_time', 'status', 'created_at')
    list_filter = ('status', 'start_time', 'end_time')
    search_fields = ('message__subject',)
    filter_horizontal = ('recipients',)
    readonly_fields = ('status', 'created_at')
    inlines = [MailingAttemptInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('message', 'recipients')
        }),
        ('Временные параметры', {
            'fields': ('start_time', 'end_time', 'status')
        }),
        ('Служебная информация', {
            'fields': ('created_at',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Делаем status и created_at только для чтения"""
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:
            return readonly
        return readonly


@admin.register(MailingAttempt)
class MailingAttemptAdmin(admin.ModelAdmin):
    """Административная панель для попыток рассылок"""

    list_display = ('id', 'mailing', 'recipient_email', 'attempt_time', 'status')
    list_filter = ('status', 'attempt_time')
    search_fields = ('mailing__message__subject', 'recipient_email', 'server_response')
    readonly_fields = ('attempt_time',)

    def has_add_permission(self, request):
        """Запрещаем ручное создание попыток"""
        return False
