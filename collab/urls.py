from django.urls import path
from . import views

app_name = "collab"

urlpatterns = [
    path('', views.index, name='index'),
    path('room/<room_name>', views.get_room_elements, name='index')
]
