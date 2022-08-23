#!/bin/bash
BASEDIR=$(cd "$(dirname "$0")"; pwd)
source $BASEDIR/init.sh

# $BASEDIR/make_static.sh
echo; echo $(colored $CYAN "collecting static files... "); echo
gosu ltiapp python manage.py collectstatic --no-input

echo; echo $(colored $CYAN "migrating database... "); echo
gosu ltiapp python manage.py migrate --settings=local_settings

echo;echo $(colored $CYAN "starting development server:"); echo
exec gosu ltiapp python manage.py runserver --settings=local_settings 0.0.0.0:8000
