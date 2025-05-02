from django.urls import path
from .views import *

urlpatterns = [
    path('search/', SearchAPIView.as_view(), name='search_api'),
    path('search/feedback/', SearchFeedbackAPIView.as_view(), name='search_result_detail_api'),
    ]