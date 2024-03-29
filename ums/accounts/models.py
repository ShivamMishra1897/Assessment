# import the required libraries
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

#base user extended fro django's in built AbstractUser 
class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_manager = models.BooleanField(default=False)
    is_executive = models.BooleanField(default=False)

class Manager(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='manager')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)

class Executive(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='executive')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)

class Clients(models.Model):
    clients = models.TextField()
    manager = models.ForeignKey(Manager, on_delete=models.CASCADE, related_name='Clients')
    created_at = models.DateTimeField(default=timezone.now)
    
#change name 
class Comment(models.Model):
    comment = models.TextField()
    clients = models.ForeignKey(Clients, on_delete=models.CASCADE, related_name='Comment')
    Executive = models.ForeignKey(Executive, on_delete=models.CASCADE, related_name='Comment')
    created_at = models.DateTimeField(default=timezone.now)