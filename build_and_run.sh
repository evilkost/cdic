#!/usr/bin/bash

echo "RUN AS ROOT"

docker build -t cdic .
docker run -d --name="cdic" -p 8000:8000 -it -v /sys/fs/cgroup:/sys/fs/cgroup:ro cdic:latest


