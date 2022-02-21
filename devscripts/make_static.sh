#!/usr/bin/env bash
BASEDIR=$(cd "$(dirname "$0")"; pwd)
source $BASEDIR/init.sh

cd $BASEDIR/../client
npm run build

cd $BASEDIR/..
python manage.py collectstatic
