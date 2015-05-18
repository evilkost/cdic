#!/usr/bin/bash


cd /opt/cdic/
git pull --force

#/opt/cdic/_docker/first_run.sh

pip3 install -r requirements.txt
cd src



su - cdic -c "alembic upgrade head"

if [ ! -d /home/cdic/.config ]
then
    su - cdic -c "mkdir -p /home/cdic/.config"
fi

su - cdic -c "touch /home/cdic/.config/cdic.py"
