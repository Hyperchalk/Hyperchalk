from django.urls import path

from . import views

app_name = 'lti'

urlpatterns = [
    path(
        'register-consumer/<uuid:pk>', views.RegisterConsumerView.as_view(),
        name="register-consumer"),
    path('config', views.login, name="login"),
    path('config', views.jwks, name="jwks"),
    path('launch', views.launch, name="launch"),
    # path('config', views.lti_config, name="config"),
]
