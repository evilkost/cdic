#!/usr/bin/bash


echo "RUN AS ROOT"
echo "depends on:"
echo "/srv/cdic/cdic.py: local setting"
echo "/srv/cdic/id_rsa: ssh key for github"

mkdir -p _docker/private
# cp $PRIVATE_GITHUB_KEY _docker/private/id_rsa

touch tmp_cache_buster
docker build -t cdic .
# docker run -d --name="cdic" -p 8000:8000 -it -v /sys/fs/cgroup:/sys/fs/cgroup:ro cdic:latest
rm tmp_cache_buster
mkdir -p /srv/cdic
# cp -f _docker/cdic_db.py /srv/cdic/cdic_db.py

docker run -d --link cdic-postgres:postgres \
    --name="cdic" -p 8000:8000 -it \
    -v /sys/fs/cgroup:/sys/fs/cgroup:rox\
    -v /srv/cdic:/etc/cdic:ro  \
    --volumes-from cdic_workdir \
    cdic:latest

#rm -rf _docker/private
