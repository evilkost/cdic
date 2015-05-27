# coding: utf-8

import os

DEBUG = True

ADMINS = frozenset(['nobody@example.com'])
SECRET_KEY = 'This string will be replaced with a proper key in production.'

SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join("/tmp", 'cdic', 'app.db')
DATABASE_CONNECT_OPTIONS = {}

CSRF_ENABLED = True
CSRF_SESSION_KEY = "somethingimpossibletoguess"

VAR_ROOT = "/var/lib/cdic"
OPENID_STORE = "/var/lib/cdic/openid"
CDIC_WORKPLACE = "/var/lib/cdic/wp"

DOCKERHUB_URL = 'https://hub.docker.com'
DOCKERREGISTRY_URL = 'https://registry.hub.docker.com'
DOCKERHUB_USERNAME = 'FILL DOCKER USERNAME'
DOCKERHUB_PASSWORD = 'FILL DOCKER PASSWORD'
HUB_PROJECT_URL_TEMPLATE = "http://registry.hub.docker.com/u/FILL DOCKER USERNAME AGAIN/{repo_name}"

GITHUB_TOKEN = "FILL GITHUB TOKEN"
GITHUB_USER = "FILL GITHUB USER"
GITHUB_API_ROOT = "https://api.github.com"
GITHUB_URL = "https://github.com"

GITHUB_PUSH_URL = "git://github.com"

COPR_BASE_URL = "https://copr.fedoraproject.org"

MAIN_LOG = "/var/log/cdic/main.log"
ASYNC_LOG = "/var/log/cdic/async.log"

