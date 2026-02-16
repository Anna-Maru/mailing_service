from django.contrib.auth.models import AbstractUser
from django.db import models
import secrets


class User(AbstractUser):
    """Расширенная модель пользователя с ролями"""

    ROLE_USER = 'user'
    ROLE_MANAGER = 'manager'
    ROLE_ADMIN = 'admin'

    ROLE_CHOICES = [
        (ROLE_USER, 'Пользователь'),
        (ROLE_MANAGER, 'Менеджер'),
        (ROLE_ADMIN, 'Администратор'),
    ]

    email = models.EmailField(unique=True, verbose_name='Email')
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_USER,
        verbose_name='Роль'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Телефон'
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Страна'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар'
    )
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name='Email подтвержден'
    )
    email_verification_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Токен подтверждения email'
    )
    is_blocked = models.BooleanField(
        default=False,
        verbose_name='Заблокирован'
    )
    blocked_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='Причина блокировки'
    )

    # Переопределение поля авторизации на email
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        """Генерация токена при создании"""
        if not self.email_verification_token:
            self.email_verification_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def is_user(self):
        """Проверка роли пользователя"""
        return self.role == self.ROLE_USER

    def is_manager(self):
        """Проверка роли менеджера"""
        return self.role == self.ROLE_MANAGER

    def is_admin_role(self):
        """Проверка роли администратора"""
        return self.role == self.ROLE_ADMIN

    def can_manage_users(self):
        """Может ли пользователь управлять другими пользователями"""
        return self.is_manager() or self.is_admin_role() or self.is_superuser

    def can_view_all_mailings(self):
        """Может ли просматривать все рассылки"""
        return self.is_manager() or self.is_admin_role() or self.is_superuser
