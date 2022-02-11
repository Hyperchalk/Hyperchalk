from uuid import UUID
from ninja import NinjaAPI
from pydantic import HttpUrl
from . import models as m
from django.shortcuts import get_object_or_404

api = NinjaAPI(urls_namespace='ltiapi', version='1.3')

@api.get('/registerconsumer/{one_off_id}')
def registerconsumer(request, one_off_id: UUID, openid_configuration: HttpUrl, registration_token: str):
    get_object_or_404()
