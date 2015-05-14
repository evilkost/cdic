#!/usr/bin/bash


echo "befor"
if [ -e /opt/cdic/_docker/init_done ]; then
    echo "already initialised"

else
    echo "initiating db"
    cd /opt/cdic/src
    PYTHONPATH=.:$PYTHONPATH /usr/bin/python3 cdic/manage.py create_db -f alembic.ini
    # alembic upgrade head

    touch /opt/cdic/_docker/init_done
fi
echo "after"

