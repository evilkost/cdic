#!/usr/bin/env bash


docker pull postgres:9.3
docker run --name cdic-postgres -e POSTGRES_PASSWORD=cdicpsqlpwd \
 -e POSTGRES_USER=cdic -e POSTGRES_DB=cdicdb -d postgres
