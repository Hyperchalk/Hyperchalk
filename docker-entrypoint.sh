#!/bin/bash

# these may be exposed as a volume but they need to be writeable.
test -d /srv/data && chown -R ltiapp:ltiapp /srv/data
test -d /srv/static_copy && chown -R ltiapp:ltiapp /srv/static_copy

if [[ "$1" == "manage" ]]; then
	# management commands for "docker run --rm buvo-tool manage ..."
  shift
  gosu ltiapp:ltiapp python3 manage.py $@
else
	# drop privileges to run the server
	gosu ltiapp:ltiapp bash <<- EOF
		python manage.py collectstatic --noinput
		python manage.py migrate
		gunicorn -k buvo.uvicorn.UvicornWorker $@
	EOF
fi
