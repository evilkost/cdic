#!/usr/bin/bash


cd /opt/cdic/
git pull --force

/opt/cdic/_docker/first_run.sh

cd src
alembic upgrade head

cd /opt/cdic/src/cdic
python3-gunicorn app:app -b '0.0.0.0:8080'
