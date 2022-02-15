from django.urls import path

from .urlconf import ws_include

urlpatterns = [
    path('collab/', ws_include('collab.urls_ws'))
]
