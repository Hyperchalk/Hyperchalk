#!/bin/bash
BASEDIR=$(cd "$(dirname "$0")"; pwd)
cd $BASEDIR/..

$BASEDIR/make_static.sh

gosu moodle ENV/bin/python manage.py migrate --settings=local_settings
gosu moodle ENV/bin/python manage.py runserver --settings=local_settings
