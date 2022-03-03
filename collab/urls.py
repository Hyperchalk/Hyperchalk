from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "collab"

urlpatterns = [
    path('', views.index, name='index'),
    path('room/<room_name>', views.get_current_elements, name='room'),
    path('record/<int:pk>', views.get_log_record, name='record'),
    path('add-library', TemplateView.as_view(template_name='collab/add_library.html'),
         name='add-library')
]
