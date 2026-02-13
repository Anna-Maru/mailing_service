from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Client, Message, Mailing


class ClientForm(forms.ModelForm):
    """Форма для клиента"""

    class Meta:
        model = Client
        fields = ['email', 'full_name', 'comment']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@mail.com'
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Иванов Иван Иванович'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Дополнительная информация о клиенте'
            }),
        }


class MessageForm(forms.ModelForm):
    """Форма для сообщения"""

    class Meta:
        model = Message
        fields = ['subject', 'body']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Тема письма'
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Текст письма'
            }),
        }


class MailingForm(forms.ModelForm):
    """Форма для рассылки"""

    class Meta:
        model = Mailing
        fields = ['message', 'recipients', 'start_time', 'end_time']
        widgets = {
            'message': forms.Select(attrs={
                'class': 'form-control'
            }),
            'recipients': forms.CheckboxSelectMultiple(),
            'start_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Фильтруем сообщения и клиентов по текущему пользователю
        if user:
            self.fields['message'].queryset = Message.objects.filter(owner=user)
            self.fields['recipients'].queryset = Client.objects.filter(owner=user)

        # Если объект уже существует, форматируем даты для input type="datetime-local"
        if self.instance and self.instance.pk:
            if self.instance.start_time:
                self.initial['start_time'] = self.instance.start_time.strftime('%Y-%m-%dT%H:%M')
            if self.instance.end_time:
                self.initial['end_time'] = self.instance.end_time.strftime('%Y-%m-%dT%H:%M')

    def clean_start_time(self):
        """Валидация времени начала"""
        start_time = self.cleaned_data.get('start_time')

        # Проверяем только для новых объектов
        if not self.instance.pk and start_time:
            if start_time < timezone.now():
                raise ValidationError('Дата начала не может быть в прошлом.')

        return start_time

    def clean(self):
        """Валидация всей формы"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time:
            if start_time >= end_time:
                raise ValidationError({
                    'end_time': 'Дата окончания должна быть позже даты начала.'
                })

        return cleaned_data
