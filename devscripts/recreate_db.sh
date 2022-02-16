#!/usr/bin/env bash
BASEDIR=$(cd "$(dirname "$0")"; pwd)
source $BASEDIR/init.sh
cd $BASEDIR/..

mv db.sqlite3 db.sqlite3.old

$BASEDIR/../manage.py migrate
$BASEDIR/create_admin.sh
