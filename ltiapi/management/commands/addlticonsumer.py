import json
import os

import djclick as click
from django.conf import settings

from ltiapi.types import LtiConfig

from ltiapi import models as m


@click.command()
@click.option('--consumer', prompt='Consumer URL')
@click.option()
def command():
    # TODO: implement
    raise NotImplementedError()
