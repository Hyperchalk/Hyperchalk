#!/bin/bash
# This prepares the django translation files. You can either prepare
# the translations (-m), compile them (-m) or do both.

BASEDIR=$(cd "$(dirname "$0")"; pwd)
source $BASEDIR/init.sh

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -c|--compile)
      M_COMPILE=true
      shift # past argument=value
    ;;
    -m|--make)
      M_MAKE=true
      shift # past argument=value
    ;;
    *)
      echo ""
      # unknown option
    ;;
  esac
done

if ! [[ $M_COMPILE || $M_MAKE ]]; then
  M_MAKE=true
  M_COMPILE=true
fi

if [ $M_MAKE ]; then
  python manage.py makemessages --locale=de \
    --ignore="client" \
    --ignore="devscripts" \
    --ignore="ENV" \
    --ignore="htmlcov" \
    --ignore="tmp" \
    --add-location="file"
fi

if [ $M_COMPILE ]; then
  python manage.py compilemessages --locale=de
fi
