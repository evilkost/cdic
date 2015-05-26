# coding: utf-8

import os

pg_host = os.env["POSTGRES_PORT_5432_TCP_ADDR"]
pg_port = os.env["POSTGRES_PORT_5432_TCP_PORT"]
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://cdic:cdicpsqlpwd@{}:{}/cdicdb'.format(pg_host, pg_port)
DATABASE_CONNECT_OPTIONS = {}
