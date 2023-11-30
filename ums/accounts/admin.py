from django.contrib import admin
from .models import User, Clients, Comment, Manager,Executive

admin.site.register(User)
admin.site.register(Clients)
admin.site.register(Comment)
admin.site.register(Manager)
admin.site.register(Executive)