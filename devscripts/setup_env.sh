#!/bin/bash
BASEDIR=$(cd "$(dirname "$0")"; pwd)
cd $BASEDIR/..

rm -rf ENV
python3 -m venv ENV
ENV/bin/python -m pip install -U pip wheel setuptools
ENV/bin/python -m pip install -r requirements.txt
