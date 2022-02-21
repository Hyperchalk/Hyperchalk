#!/bin/bash
BASEDIR=$(cd "$(dirname "$0")"; pwd)
cd $BASEDIR/..

$BASEDIR/make_static.sh

echo $(colored $CYAN "migrating database... ")
gosu moodle ENV/bin/python manage.py migrate --settings=local_settings

echo $(colored $CYAN "starting development server:")
gosu moodle ENV/bin/python manage.py runserver --settings=local_settings
