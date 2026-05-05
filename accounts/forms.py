# accounts/forms.py
from django import forms
from .models import User
from django.conf import settings


class RegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    admin_key = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ['username', 'password', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'w-full mt-1 p-2 border rounded focus:ring-2 focus:ring-green-500 focus:outline-none'
            })

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        admin_key = cleaned_data.get('admin_key')

        if role == 'admin':
            if admin_key != settings.ADMIN_CREATION_KEY:
                raise forms.ValidationError("Invalid admin pass key")

        return cleaned_data
