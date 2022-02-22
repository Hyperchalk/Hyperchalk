#!/usr/bin/env bash
BASEDIR=$(cd "$(dirname "$0")"; pwd)
source $BASEDIR/init.sh

echo $(colored $CYAN "installing client libs... ")
cd $BASEDIR/../client
npm install

echo $(colored $CYAN "building client... ")
cd $BASEDIR/../client
npm run build

echo $(colored $CYAN "collecting static files... ")
cd $BASEDIR/..
python manage.py collectstatic --no-input
