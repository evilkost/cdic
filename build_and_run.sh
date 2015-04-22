#!/usr/bin/bash

echo "RUN AS ROOT"

docker build -t cdic .
docker run  -p 8080:8080 -t -i --name cdic_test cdic


