#!/bin/bash
# this will run the tests, make a coverage report and open it

# OPTIONS:
#   --no-open   don't open the report index after running
#   MODULE      positional argument to specify a module to test

BASEDIR=$(cd "$(dirname "$0")"; pwd)
source $BASEDIR/init.sh

NO_OPEN=false
XML=false

POSARGS=()

while [[ $# -gt 0 ]]; do
  case $1 in
    --no-open)
      shift
      NO_OPEN=true
      ;;
    --xml)
      XML=true
      shift
      ;;
    *)
      POSARGS+=($1)
      shift
      ;;
  esac
done

set -- "${POSARGS[@]}"
TEST_ONLY=$1

coverage run --source='.' manage.py test $1

if [[ "$XML" = true ]]; then
  echo "Generating xml coverage report."
  coverage xml
else
  echo "Generating html coverage report."
  coverage html

  if [ $NO_OPEN = false ] && [ $(command -v open) ]; then
    open "htmlcov/index.html"
  fi
fi
