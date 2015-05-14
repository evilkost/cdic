#!/usr/bin/bash

PRIVATE_CONF_PATH=$1
PRIVATE_GITHUB_KEY=$2

if [ ! -e $PRIVATE_CONF_PATH ]
then
    echo "Missing first argument: path to the private config"
    exit 1
fi

if [ ! -e $PRIVATE_GITHUB_KEY ]
then
    echo "Missing second argument: path to the private ssh key for gihub"
    exit 2
fi

echo "RUN AS ROOT"

cp $PRIVATE_CONF_PATH _docker/cdic.py
cp $PRIVATE_GITHUB_KEY _docker/id_rsa

docker build -t cdic .
docker run -d --name="cdic" -p 8000:8000 -it -v /sys/fs/cgroup:/sys/fs/cgroup:ro cdic:latest

rm -f _docker/cdic.py
rm -f _docker/id_rsa
