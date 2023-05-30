#!/bin/bash

set -euo pipefail

# these may be exposed as a volume but they need to be writeable.
test -d /srv/data && chown -R ltiapp:ltiapp /srv/data
test -d /srv/static_copy && chown -R ltiapp:ltiapp /srv/static_copy

if [[ "$1" == "manage" ]]; then
	# management commands for "docker run --rm hyperchalk manage ..."
  shift
  exec gosu ltiapp:ltiapp python3 manage.py $@
else
	# drop privileges to run the server
	exec gosu ltiapp:ltiapp bash <<- EOF
    set -euo pipefail
		python manage.py migrate
		python manage.py collectstatic --noinput
		exec gunicorn -k draw.uvicorn.UvicornWorker $@
	EOF
fi
