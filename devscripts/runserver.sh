#!/bin/bash
BASEDIR=$(cd "$(dirname "$0")"; pwd)
source $BASEDIR/init.sh

$BASEDIR/make_static.sh

echo; echo $(colored $CYAN "migrating database... "); echo
gosu moodle ENV/bin/python manage.py migrate --settings=local_settings

echo;echo $(colored $CYAN "starting development server:"); echo
gosu moodle ENV/bin/python manage.py runserver --settings=local_settings 127.0.0.1:8001
