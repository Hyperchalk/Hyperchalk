from django.urls import path

from . import views

app_name = 'lti'
urlpatterns = [
    path('config', views.lti_config, name="config"),
    path('launch', views.lti_launch, name="launch"),
]
