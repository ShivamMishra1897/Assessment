from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Manager, Executive,Clients,Comment
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class ManagerSignUpForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput())
    password1 = forms.CharField(widget=forms.PasswordInput())
    password2 = forms.CharField(widget=forms.PasswordInput())

    first_name = forms.CharField(widget=forms.TextInput())
    last_name = forms.CharField(widget=forms.TextInput())

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_manager = True
        if commit:
            user.save()
        manager = Manager.objects.create(user=user, first_name=self.cleaned_data.get('first_name'), last_name=self.cleaned_data.get('last_name'))
        return user
    
class ExecutiveSignUpForm(UserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput())
    password1 = forms.CharField(widget=forms.PasswordInput())
    password2 = forms.CharField(widget=forms.PasswordInput())

    first_name = forms.CharField(widget=forms.TextInput())
    last_name = forms.CharField(widget=forms.TextInput())

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_executive = True
        if commit:
            user.save()
        executive = Executive.objects.create(user=user, first_name=self.cleaned_data.get('first_name'), last_name=self.cleaned_data.get('last_name'))
        return user
    
class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput())
    password = forms.CharField(widget=forms.PasswordInput())

class ClientForm(forms.ModelForm):
    clients = forms.CharField(widget=forms.Textarea())

    class Meta:
        model = Clients
        fields = ('clients',)

class CommentForm(forms.ModelForm):
    answer = forms.CharField(widget=forms.Textarea())

    class Meta:
        model = Comment
        fields = ('comment',)