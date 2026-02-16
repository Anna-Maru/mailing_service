from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView)
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q, Count
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from .models import Client, Message, Mailing, MailingAttempt
from .forms import ClientForm, MessageForm, MailingForm


class OwnerRequiredMixin:
    """Mixin для проверки владельца объекта"""

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Менеджеры и админы видят все
        if user.can_view_all_mailings():
            return queryset

        # Обычные пользователи только свои
        return queryset.filter(owner=user)


class OwnerOrManagerRequiredMixin:
    """Mixin для проверки прав редактирования"""

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        user = request.user

        # Если это владелец или менеджер/админ
        if obj.owner == user or user.can_view_all_mailings():
            # Менеджер не может редактировать чужие объекты
            if user.is_manager() and obj.owner != user:
                if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                    messages.error(
                        request,
                        'Менеджер может просматривать, но не редактировать чужие данные.'
                    )
                    return redirect(self.get_success_url())
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, 'У вас нет прав доступа к этому объекту.')
        return redirect('mailings:home')


@method_decorator(cache_page(settings.CACHE_TIMEOUT_SHORT), name='dispatch')
class HomeView(TemplateView):
    """Главная страница со статистикой"""

    template_name = 'mailings/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            user = self.request.user

            # Обновляем статусы рассылок пользователя
            user_mailings = Mailing.objects.filter(
                owner=user) if not user.can_view_all_mailings() else Mailing.objects.all()
            for mailing in user_mailings:
                mailing.update_status()

            # Статистика для текущего пользователя или общая для менеджера
            if user.can_view_all_mailings():
                mailings = Mailing.objects.all()
                clients = Client.objects.all()
            else:
                mailings = Mailing.objects.filter(owner=user)
                clients = Client.objects.filter(owner=user)

            context['total_mailings'] = mailings.count()
            context['active_mailings'] = mailings.filter(
                status=Mailing.STATUS_STARTED,
                is_active=True
            ).count()
            context['unique_clients'] = clients.count()

            # Дополнительная статистика для пользователя
            if not user.can_view_all_mailings():
                attempts = MailingAttempt.objects.filter(mailing__owner=user)
                context['total_sent'] = attempts.count()
                context['successful_sent'] = attempts.filter(
                    status=MailingAttempt.STATUS_SUCCESS
                ).count()
                context['failed_sent'] = attempts.filter(
                    status=MailingAttempt.STATUS_FAILED
                ).count()
        else:
            # Для неавторизованных общая статистика
            context['total_mailings'] = Mailing.objects.count()
            context['active_mailings'] = Mailing.objects.filter(
                status=Mailing.STATUS_STARTED
            ).count()
            context['unique_clients'] = Client.objects.count()

        return context


class ClientListView(LoginRequiredMixin, OwnerRequiredMixin, ListView):
    """Список клиентов"""

    model = Client
    template_name = 'mailings/client_list.html'
    context_object_name = 'clients'
    paginate_by = 10


class ClientDetailView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, DetailView):
    """Детальная информация о клиенте"""

    model = Client
    template_name = 'mailings/client_detail.html'
    context_object_name = 'client'


class ClientCreateView(LoginRequiredMixin, CreateView):
    """Создание клиента"""

    model = Client
    form_class = ClientForm
    template_name = 'mailings/client_form.html'
    success_url = reverse_lazy('mailings:client_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Клиент успешно добавлен!')
        return super().form_valid(form)


class ClientUpdateView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, UpdateView):
    """Редактирование клиента"""

    model = Client
    form_class = ClientForm
    template_name = 'mailings/client_form.html'
    success_url = reverse_lazy('mailings:client_list')

    def form_valid(self, form):
        messages.success(self.request, 'Клиент успешно обновлен!')
        return super().form_valid(form)


class ClientDeleteView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, DeleteView):
    """Удаление клиента"""

    model = Client
    template_name = 'mailings/client_confirm_delete.html'
    success_url = reverse_lazy('mailings:client_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Клиент успешно удален!')
        return super().delete(request, *args, **kwargs)


class MessageListView(LoginRequiredMixin, OwnerRequiredMixin, ListView):
    """Список сообщений"""

    model = Message
    template_name = 'mailings/message_list.html'
    context_object_name = 'messages_list'
    paginate_by = 10


class MessageDetailView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, DetailView):
    """Детальная информация о сообщении"""

    model = Message
    template_name = 'mailings/message_detail.html'
    context_object_name = 'message'


class MessageCreateView(LoginRequiredMixin, CreateView):
    """Создание сообщения"""

    model = Message
    form_class = MessageForm
    template_name = 'mailings/message_form.html'
    success_url = reverse_lazy('mailings:message_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Сообщение успешно создано!')
        return super().form_valid(form)


class MessageUpdateView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, UpdateView):
    """Редактирование сообщения"""

    model = Message
    form_class = MessageForm
    template_name = 'mailings/message_form.html'
    success_url = reverse_lazy('mailings:message_list')

    def form_valid(self, form):
        messages.success(self.request, 'Сообщение успешно обновлено!')
        return super().form_valid(form)


class MessageDeleteView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, DeleteView):
    """Удаление сообщения"""

    model = Message
    template_name = 'mailings/message_confirm_delete.html'
    success_url = reverse_lazy('mailings:message_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Сообщение успешно удалено!')
        return super().delete(request, *args, **kwargs)


class MailingListView(LoginRequiredMixin, OwnerRequiredMixin, ListView):
    """Список рассылок"""

    model = Mailing
    template_name = 'mailings/mailing_list.html'
    context_object_name = 'mailings'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        # Обновляем статусы всех рассылок
        for mailing in queryset:
            mailing.update_status()
        return queryset


class MailingDetailView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, DetailView):
    """Детальная информация о рассылке"""

    model = Mailing
    template_name = 'mailings/mailing_detail.html'
    context_object_name = 'mailing'

    def get_object(self, queryset=None):
        """Обновляем статус при просмотре"""
        obj = super().get_object(queryset)
        obj.update_status()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавляем историю попыток
        context['attempts'] = self.object.attempts.all()[:10]
        return context


class MailingCreateView(LoginRequiredMixin, CreateView):
    """Создание рассылки"""

    model = Mailing
    form_class = MailingForm
    template_name = 'mailings/mailing_form.html'
    success_url = reverse_lazy('mailings:mailing_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Рассылка успешно создана!')
        return super().form_valid(form)


class MailingUpdateView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, UpdateView):
    """Редактирование рассылки"""

    model = Mailing
    form_class = MailingForm
    template_name = 'mailings/mailing_form.html'
    success_url = reverse_lazy('mailings:mailing_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Рассылка успешно обновлена!')
        return super().form_valid(form)


class MailingDeleteView(LoginRequiredMixin, OwnerOrManagerRequiredMixin, DeleteView):
    """Удаление рассылки"""

    model = Mailing
    template_name = 'mailings/mailing_confirm_delete.html'
    success_url = reverse_lazy('mailings:mailing_list')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Рассылка успешно удалена!')
        return super().delete(request, *args, **kwargs)


@login_required
def send_mailing(request, pk):
    """Ручная отправка рассылки"""
    mailing = get_object_or_404(Mailing, pk=pk)

    # Проверка прав доступа
    if mailing.owner != request.user and not request.user.can_view_all_mailings():
        messages.error(request, 'У вас нет прав для отправки этой рассылки.')
        return redirect('mailings:mailing_list')

    # Проверка активности рассылки
    if not mailing.is_active:
        messages.error(
            request,
            'Рассылка деактивирована менеджером и не может быть отправлена.'
        )
        return redirect('mailings:mailing_detail', pk=pk)

    # Проверяем возможность отправки
    if not mailing.can_send():
        messages.error(
            request,
            'Рассылка не может быть отправлена. '
            'Текущее время должно быть между датой начала и окончания.'
        )
        return redirect('mailings:mailing_detail', pk=pk)

    # Получаем всех получателей
    recipients = mailing.recipients.all()

    if not recipients.exists():
        messages.warning(request, 'У рассылки нет получателей!')
        return redirect('mailings:mailing_detail', pk=pk)

    # Счетчики
    success_count = 0
    failed_count = 0

    # Отправляем письма каждому получателю
    for client in recipients:
        try:
            send_mail(
                subject=mailing.message.subject,
                message=mailing.message.body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[client.email],
                fail_silently=False,
            )

            # Создаем запись об успешной попытке
            MailingAttempt.objects.create(
                mailing=mailing,
                status=MailingAttempt.STATUS_SUCCESS,
                server_response='Письмо успешно отправлено',
                recipient_email=client.email
            )
            success_count += 1

        except Exception as e:
            # Создаем запись о неудачной попытке
            MailingAttempt.objects.create(
                mailing=mailing,
                status=MailingAttempt.STATUS_FAILED,
                server_response=str(e),
                recipient_email=client.email
            )
            failed_count += 1

    # Обновляем статус рассылки
    mailing.update_status()

    # Выводим сообщение о результатах
    if success_count > 0:
        messages.success(
            request,
            f'Успешно отправлено писем: {success_count}'
        )

    if failed_count > 0:
        messages.warning(
            request,
            f'Не удалось отправить писем: {failed_count}'
        )

    return redirect('mailings:mailing_detail', pk=pk)


@login_required
def toggle_mailing_active(request, pk):
    """Деактивация/активация рассылки. Для менеджера"""
    if not request.user.can_manage_users():
        messages.error(request, 'У вас нет прав для выполнения этого действия.')
        return redirect('mailings:home')

    mailing = get_object_or_404(Mailing, pk=pk)
    mailing.is_active = not mailing.is_active
    mailing.save()

    action = 'активирована' if mailing.is_active else 'деактивирована'
    messages.success(request, f'Рассылка успешно {action}.')

    return redirect('mailings:mailing_detail', pk=pk)


@login_required
@cache_page(settings.CACHE_TIMEOUT_SHORT)
def user_statistics(request):
    """Статистика для текущего пользователя"""
    user = request.user

    # Получаем рассылки пользователя
    user_mailings = Mailing.objects.filter(owner=user)

    # Статистика по рассылкам
    stats = {
        'total_mailings': user_mailings.count(),
        'created_mailings': user_mailings.filter(status=Mailing.STATUS_CREATED).count(),
        'active_mailings': user_mailings.filter(status=Mailing.STATUS_STARTED).count(),
        'completed_mailings': user_mailings.filter(status=Mailing.STATUS_COMPLETED).count(),
        'deactivated_mailings': user_mailings.filter(is_active=False).count(),
    }

    # Статистика по попыткам
    attempts = MailingAttempt.objects.filter(mailing__owner=user)
    stats['total_attempts'] = attempts.count()
    stats['successful_attempts'] = attempts.filter(
        status=MailingAttempt.STATUS_SUCCESS
    ).count()
    stats['failed_attempts'] = attempts.filter(
        status=MailingAttempt.STATUS_FAILED
    ).count()

    # Процент успешности
    if stats['total_attempts'] > 0:
        stats['success_rate'] = round(
            (stats['successful_attempts'] / stats['total_attempts']) * 100, 2
)
    else:
        stats['success_rate'] = 0

    # Количество клиентов
    stats['total_clients'] = Client.objects.filter(owner=user).count()

    # Количество сообщений
    stats['total_messages'] = Message.objects.filter(owner=user).count()

    return render(request, 'mailings/statistics.html', {'stats': stats})
