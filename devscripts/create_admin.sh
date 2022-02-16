#!/usr/bin/env bash
BASEDIR=$(cd "$(dirname "$0")"; pwd)
source $BASEDIR/init.sh

cd $BASEDIR/..

echo
printf "Creating admin user with password adminadmin... "

./manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.create_user('admin', password='adminadmin')
user.is_superuser = True
user.is_staff = True
user.save()
EOF

echo $(colored $LIGHT_GREEN "OK")
