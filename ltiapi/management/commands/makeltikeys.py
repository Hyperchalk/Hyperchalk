import os

import djclick as click
from django.conf import settings
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiToolKey

from ltiapi.utils import ensure_lti_config_dir_exists, generate_key_pair

# TODO: get keys from db instead of generating them here -> rename: exportkeys


@click.command()
@click.option(
    '-k', '--keyfile', default='lti', help=(
        'The file name of the key. E.g. "key" would be '
        'stored as "key.prv.pem" and "key.pub.pem".'))
@click.option(
    '-f', '--force', default=False, is_flag=True,
    help='Override key files if they already exist.')
def command(keyfile, force):
    ensure_lti_config_dir_exists()
    private_key_path = settings.LTI_CONFIG_DIR / f'{keyfile}.prv.pem'
    public_key_path = settings.LTI_CONFIG_DIR / f'{keyfile}.pub.pem'

    if os.path.isfile(private_key_path) and not force:
        print(
            f"The given key file ({private_key_path}) already exists!\nPlease "
            "use another file name via the '--keyfile' option or confirm that "
            "you know what you are doing by setting the '--force' flag.")
        exit(1)

    key_pair = generate_key_pair()

    with open (private_key_path, "w") as prv_file:
        print(key_pair['private'], file=prv_file)

    with open (public_key_path, "w") as pub_file:
        print(key_pair['public'], file=pub_file)
