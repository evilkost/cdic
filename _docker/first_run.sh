#!/usr/bin/bash

env &> /tmp/ga.log

echo "befor"
cd /opt/cdic
git pull
cd /opt/cdic/src

if [ -e /home/cdic/init_done ]; then
    echo "db schema upgrade "
    alembic upgrade head
else
    echo "initiating db"
    PYTHONPATH=.:$PYTHONPATH /usr/bin/python3 cdic/manage.py create_db -f alembic.ini
    touch /home/cdic/init_done
fi
echo "after"

