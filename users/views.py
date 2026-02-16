from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, ListView, DetailView
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetConfirmView,
    PasswordResetDoneView, PasswordResetCompleteView
)
from .models import User
from .forms import (
    UserRegisterForm, UserLoginForm, UserProfileForm,
    CustomPasswordResetForm, CustomSetPasswordForm, UserBlockForm
)


class RegisterView(CreateView):
    """Регистрация нового пользователя"""

    model = User
    form_class = UserRegisterForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        # Отправка письма с подтверждением
        verification_url = self.request.build_absolute_uri(
            f'/users/verify-email/{user.email_verification_token}/'
        )

        try:
            send_mail(
                subject='Подтверждение регистрации',
                message=f'Для подтверждения регистрации перейдите по ссылке: {verification_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            messages.success(
                self.request,
                'Регистрация успешна! Проверьте email для подтверждения регистрации.'
            )
        except Exception as e:
            messages.warning(
                self.request,
                f'Регистрация успешна, но письмо не отправлено: {str(e)}'
            )

        return redirect(self.success_url)


def verify_email(request, token):
    """Подтверждение email"""
    try:
        user = User.objects.get(email_verification_token=token)
        user.is_email_verified = True
        user.is_active = True
        user.save()

        messages.success(request, 'Email успешно подтвержден! Теперь вы можете войти.')
        return redirect('users:login')
    except User.DoesNotExist:
        messages.error(request, 'Неверная ссылка подтверждения.')
        return redirect('users:register')


def login_view(request):
    """Вход пользователя"""
    if request.user.is_authenticated:
        return redirect('mailings:home')

    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                if user.is_blocked:
                    messages.error(
                        request,
                        f'Ваш аккаунт заблокирован. Причина: {user.blocked_reason or "Не указана"}'
                    )
                else:
                    login(request, user)
                    messages.success(request, f'Добро пожаловать, {user.username}!')
                    next_url = request.GET.get('next', 'mailings:home')
                    return redirect(next_url)
    else:
        form = UserLoginForm()

    return render(request, 'users/login.html', {'form': form})


@login_required
def logout_view(request):
    """Выход пользователя"""
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('users:login')


class ProfileView(LoginRequiredMixin, UpdateView):
    """Просмотр и редактирование профиля"""

    model = User
    form_class = UserProfileForm
    template_name = 'users/profile.html'
    success_url = reverse_lazy('users:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Профиль успешно обновлен!')
        return super().form_valid(form)


class ManagerRequiredMixin(UserPassesTestMixin):
    """Mixin для проверки прав менеджера"""

    def test_func(self):
        return (
                self.request.user.is_authenticated and
                self.request.user.can_manage_users()
        )

    def handle_no_permission(self):
        messages.error(self.request, 'У вас нет прав для доступа к этой странице.')
        return redirect('mailings:home')


class UserListView(LoginRequiredMixin, ManagerRequiredMixin, ListView):
    """Список пользователей (для менеджера)"""

    model = User
    template_name = 'users/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        return User.objects.all().order_by('-date_joined')


class UserDetailView(LoginRequiredMixin, ManagerRequiredMixin, DetailView):
    """Детальная информация о пользователе (для менеджера)"""

    model = User
    template_name = 'users/user_detail.html'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()

        # Статистика пользователя
        from mailings.models import Mailing, MailingAttempt

        user_mailings = Mailing.objects.filter(owner=user)
        context['total_mailings'] = user_mailings.count()
        context['active_mailings'] = user_mailings.filter(
            status=Mailing.STATUS_STARTED
        ).count()

        # Статистика попыток
        all_attempts = MailingAttempt.objects.filter(mailing__owner=user)
        context['total_attempts'] = all_attempts.count()
        context['successful_attempts'] = all_attempts.filter(
            status=MailingAttempt.STATUS_SUCCESS
        ).count()
        context['failed_attempts'] = all_attempts.filter(
            status=MailingAttempt.STATUS_FAILED
        ).count()

        return context


@login_required
def toggle_user_block(request, pk):
    """Блокировка/разблокировка пользователя (для менеджера)"""
    if not request.user.can_manage_users():
        messages.error(request, 'У вас нет прав для блокировки пользователей.')
        return redirect('mailings:home')

    user = get_object_or_404(User, pk=pk)

    # Нельзя заблокировать себя или суперпользователя
    if user == request.user:
        messages.error(request, 'Вы не можете заблокировать себя.')
        return redirect('users:user_list')

    if user.is_superuser:
        messages.error(request, 'Нельзя заблокировать суперпользователя.')
        return redirect('users:user_list')

    if request.method == 'POST':
        form = UserBlockForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            action = 'заблокирован' if user.is_blocked else 'разблокирован'
            messages.success(
                request,
                f'Пользователь {user.username} успешно {action}.'
            )
            return redirect('users:user_detail', pk=pk)
    else:
        form = UserBlockForm(instance=user)

    return render(request, 'users/user_block.html', {
        'form': form,
        'profile_user': user
    })


# Кастомные views для восстановления пароля
class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = reverse_lazy('users:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'
