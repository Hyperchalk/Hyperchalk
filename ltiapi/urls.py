from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'lti'

urlpatterns = [
    path('register-consumer/<uuid:link>', views.dynamic_consumer_registration, name="register-consumer"),
    path('privacy', TemplateView.as_view(template_name='ltiapi/privacy.html')),
    path('login', views.oidc_login, name="login"),
    path('jwks', views.oidc_jwks, name="jwks"),
    path('launch', views.lti_launch, name="launch"),
    path('configure/<launch_id>', views.lti_configure, name="configure"),
    # path('config', views.lti_config, name="config"),
]
