#!/usr/bin/bash

PRIVATE_CONF_PATH=$1

if [ ! -e $PRIVATE_CONF_PATH ]
then
    echo "Missing first argument: path to the private config"
    exit 1
fi

echo "RUN AS ROOT"

cp $PRIVATE_CONF_PATH _docker/cdic.py

docker build -t cdic .
docker run -d --name="cdic" -p 8000:8000 -it -v /sys/fs/cgroup:/sys/fs/cgroup:ro cdic:latest


