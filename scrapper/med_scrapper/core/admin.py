from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Website)
admin.site.register(SearchQuery)
admin.site.register(SearchResult)
admin.site.register(ManualCorrection)
admin.site.register(LearnedProduct)
