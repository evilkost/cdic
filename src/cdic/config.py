# coding: utf-8

import os

DEBUG = True

ADMINS = frozenset(['nobody@example.com'])
SECRET_KEY = 'This string will be replaced with a proper key in production.'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join("/tmp", 'cdic', 'app.db')
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"


OPENID_STORE = "/tmp/cdic/openid/"

CDIC_WORKPLACE = "/tmp/cdic/wp"
COPR_FRONTEND_URL = "http://copr.fedoraproject.org"  # base url to the copr instance