from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings


class Client(models.Model):
    """Модель получателя рассылки"""

    email = models.EmailField(verbose_name='Email')
    full_name = models.CharField(max_length=255, verbose_name='Ф.И.О.')
    comment = models.TextField(blank=True, null=True, verbose_name='Комментарий')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clients',
        verbose_name='Владелец',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['full_name']
        unique_together = ['email', 'owner']
        permissions = [
            ('can_view_all_clients', 'Может просматривать всех клиентов'),
            ('can_disable_client', 'Может отключать клиентов'),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class Message(models.Model):
    """Модель сообщения для рассылки"""

    subject = models.CharField(max_length=255, verbose_name='Тема письма')
    body = models.TextField(verbose_name='Тело письма')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Владелец',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['-created_at']
        permissions = [
            ('can_view_all_messages', 'Может просматривать все сообщения'),
            ('can_disable_message', 'Может отключать сообщения'),
        ]

    def __str__(self):
        return self.subject


class Mailing(models.Model):
    """Модель рассылки"""

    STATUS_CREATED = 'Создана'
    STATUS_STARTED = 'Запущена'
    STATUS_COMPLETED = 'Завершена'

    STATUS_CHOICES = [
        (STATUS_CREATED, 'Создана'),
        (STATUS_STARTED, 'Запущена'),
        (STATUS_COMPLETED, 'Завершена'),
    ]

    start_time = models.DateTimeField(verbose_name='Дата и время начала')
    end_time = models.DateTimeField(verbose_name='Дата и время окончания')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
        verbose_name='Статус'
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='mailings',
        verbose_name='Сообщение'
    )
    recipients = models.ManyToManyField(
        Client,
        related_name='mailings',
        verbose_name='Получатели'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mailings',
        verbose_name='Владелец',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна',
        help_text='Менеджер может деактивировать рассылку'
    )

    class Meta:
        verbose_name = 'Рассылка'
        verbose_name_plural = 'Рассылки'
        ordering = ['-created_at']
        permissions = [
            ('can_view_all_mailings', 'Может просматривать все рассылки'),
            ('can_disable_mailing', 'Может отключать рассылки'),
        ]

    def __str__(self):
        return f"Рассылка #{self.pk} - {self.message.subject}"

    def clean(self):
        """Валидация полей модели"""
        if self.start_time and self.end_time:
            # Проверяем, что start_time раньше end_time
            if self.start_time >= self.end_time:
                raise ValidationError({
                    'end_time': 'Дата окончания должна быть позже даты начала.'
                })

            # Проверяем, что start_time не в прошлом (только для новых объектов)
            if not self.pk and self.start_time < timezone.now():
                raise ValidationError({
                    'start_time': 'Дата начала не может быть в прошлом.'
                })

    def update_status(self):
        """Динамическое обновление статуса рассылки на основе текущего времени"""
        now = timezone.now()

        if now < self.start_time:
            new_status = self.STATUS_CREATED
        elif self.start_time <= now <= self.end_time:
            new_status = self.STATUS_STARTED
        else:
            new_status = self.STATUS_COMPLETED

        # Обновляем статус только если он изменился
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=['status'])

    def is_active(self):
        """Проверка, является ли рассылка активной"""
        self.update_status()
        return self.status == self.STATUS_STARTED

    def can_send(self):
        """Проверка возможности отправки рассылки"""
        now = timezone.now()
        return self.start_time <= now <= self.end_time


class MailingAttempt(models.Model):
    """Модель попытки рассылки"""

    STATUS_SUCCESS = 'Успешно'
    STATUS_FAILED = 'Не успешно'

    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Успешно'),
        (STATUS_FAILED, 'Не успешно'),
    ]

    mailing = models.ForeignKey(
        Mailing,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name='Рассылка'
    )
    attempt_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата и время попытки'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name='Статус'
    )
    server_response = models.TextField(
        blank=True,
        null=True,
        verbose_name='Ответ почтового сервера'
    )
    recipient_email = models.EmailField(
        verbose_name='Email получателя',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Попытка рассылки'
        verbose_name_plural = 'Попытки рассылок'
        ordering = ['-attempt_time']

    def __str__(self):
        return f"Попытка #{self.pk} - {self.mailing} - {self.status}"
