#!/usr/bin/bash

PRIVATE_GITHUB_KEY=$1

if [ ! -e $PRIVATE_GITHUB_KEY ]
then
    echo "Missing argument: path to the private ssh key for gihub"
    exit 1
fi

echo "RUN AS ROOT"

mkdir _docker/private
#cp $PRIVATE_CONF_PATH _docker/private/cdic.py
cp $PRIVATE_GITHUB_KEY _docker/private/id_rsa

docker build -t cdic .
# docker run -d --name="cdic" -p 8000:8000 -it -v /sys/fs/cgroup:/sys/fs/cgroup:ro cdic:latest

mkdir -p /srv/cdic
cp -f _docker/cdic_db.py /srv/cdic_db.py

docker run -d --link cdic-postgres:postgres --name="cdic" -p 8000:8000 -it -v /sys/fs/cgroup:/sys/fs/cgroup:ro cdic:latest

rm -rf _docker/private
