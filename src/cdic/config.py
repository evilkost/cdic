# coding: utf-8

import os

DEBUG = False

ADMINS = frozenset(['nobody@example.com'])
SECRET_KEY = 'This string will be replaced with a proper key in production.'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join("/tmp", 'cdic', 'app.db')
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"
