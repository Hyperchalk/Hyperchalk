#!/bin/sh
# this script provides some basic functionality for sourcing
# in other devscripts. After execution, the working directory
# will be the project root. Also it may activate a virtual env
# if none is active and one is found at the project root.

if [ -z $BASEDIR ]; then
  BASEDIR=$(cd "$(dirname "$0")"; pwd)
fi

cd "$BASEDIR/.."

# activate venv
if [[ -d "ENV" && -z "$VIRTUAL_ENV" ]]; then
  source ENV/bin/activate
fi

if [[ -f '.env' ]]; then
  source .env
fi

# makes a typical yes/no prompt. call via:
# VAR=$(read_while $QUESTION_STRING)
function read_while {
  QUESTION="$1"
  while true; do
    read -p "$QUESTION [y/n] " READ_WHILE_OUT

    if [[ "$READ_WHILE_OUT" != "y" && "$READ_WHILE_OUT" != "n" ]]; then
      echo "Only 'y' or 'n' can be accepted here." >&2
    else
      break
    fi
  done
  echo $READ_WHILE_OUT
}

BLACK='\033[0;30m'
DARK_GRAY='\033[1;30m'
RED='\033[0;31m'
LIGHT_RED='\033[1;31m'
GREEN='\033[0;32m'
LIGHT_GREEN='\033[1;32m'
BROWN_ORANGE='\033[0;33m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
LIGHT_BLUE='\033[1;34m'
PURPLE='\033[0;35m'
LIGHT_PURPLE='\033[1;35m'
CYAN='\033[0;36m'
LIGHT_CYAN='\033[1;36m'
LIGHT_GRAY='\033[0;37m'
WHITE='\033[1;37m'
COLOR_END='\033[0m'

function colored {
  printf "${1}${2}${COLOR_END}"
}

export DJANGO_SETTINGS_MODULE=draw.test_settings
