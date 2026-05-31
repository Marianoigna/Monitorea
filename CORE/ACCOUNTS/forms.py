from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import CustomUser


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(attrs={
            'placeholder': 'Usuario',
            'autofocus': True,
            'class': 'form-control',
        }),
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Contraseña',
            'class': 'form-control',
        }),
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'email@ejemplo.com',
            'class': 'form-control',
        }),
    )
    empresa = forms.CharField(
        required=True,
        max_length=150,
        label='Empresa',
        widget=forms.TextInput(attrs={
            'placeholder': 'Nombre de su empresa',
            'class': 'form-control',
        }),
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'empresa', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Nombre de usuario',
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Contraseña',
            'class': 'form-control',
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Confirmar contraseña',
            'class': 'form-control',
        })
