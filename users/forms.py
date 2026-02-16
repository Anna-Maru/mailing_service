from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm,
    PasswordResetForm, SetPasswordForm
)
from .models import User


class UserRegisterForm(UserCreationForm):
    """Форма регистрации пользователя"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя пользователя'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Пароль'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Подтверждение пароля'
        })


class UserLoginForm(AuthenticationForm):
    """Форма входа"""

    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Имя пользователя'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль'
        })
    )


class UserProfileForm(forms.ModelForm):
    """Форма редактирования профиля"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'country', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Фамилия'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 (999) 999-99-99'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Страна'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }


class CustomPasswordResetForm(PasswordResetForm):
    """Кастомная форма восстановления пароля"""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )


class CustomSetPasswordForm(SetPasswordForm):
    """Кастомная форма установки нового пароля"""

    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Новый пароль'
        })
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Подтверждение пароля'
        })
    )


class UserBlockForm(forms.ModelForm):
    """Форма блокировки пользователя (для менеджера)"""

    class Meta:
        model = User
        fields = ['is_blocked', 'blocked_reason']
        widgets = {
            'is_blocked': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'blocked_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Причина блокировки'
            }),
        }
