#!/usr/bin/bash

env &> /tmp/ga.log

echo "befor"
cd /opt/cdic
git pull
cd /opt/cdic/src

if [ -e /opt/cdic/_docker/init_done ]; then
    echo "db schema upgrade "
    alembic upgrade head
else
    echo "initiating db"
    PYTHONPATH=.:$PYTHONPATH /usr/bin/python3 cdic/manage.py create_db -f alembic.ini
    touch /opt/cdic/_docker/init_done
fi
echo "after"

