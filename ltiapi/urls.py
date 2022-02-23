from django.urls import path

from . import views

app_name = 'lti'

urlpatterns = [
    path(
        'register-consumer/<uuid:pk>', views.RegisterConsumerView.as_view(),
        name="register-consumer"),
    path('login', views.oidc_login, name="login"),
    path('jwks', views.oidc_jwks, name="jwks"),
    path('launch', views.lti_launch, name="launch"),
    # path('config', views.lti_config, name="config"),
]
