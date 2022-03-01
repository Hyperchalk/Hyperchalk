import djclick as click

from ltiapi import models as m
from draw.utils.django_loaded import build_absolute_uri_without_request
from django.urls import reverse

@click.command()
@click.option('--name', prompt='Name for the consumer (just for the admin)')
@click.option('--protocol', default='https')
def command(name, protocol):
    link = m.OneOffRegistrationLink(consumer_name=name)
    link.save()
    link_uri = build_absolute_uri_without_request(
        reverse('lti:register-consumer', args=[link.pk]),
        protocol=protocol)
    print(f'Please hand the following link to the administrator of the LTI consumer: {link_uri}')
