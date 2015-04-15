# coding: utf-8

import base64
import datetime
import functools
import re

import flask
from flask import g, session, redirect, flash, url_for

from flask_openid import OpenID

from .. import app, db
from ..models import User

auth_bp = flask.Blueprint("auth", __name__, url_prefix="/auth")
oid = OpenID(app, app.config["OPENID_STORE"], safe_roots=[])


class FasOID(object):
    uri = "https://id.fedoraproject.org/"
    oid_pre = "http://"
    oid_suf = ".id.fedoraproject.org/"

    @classmethod
    def from_username(cls, name):
        return "{}{}{}".format(cls.oid_pre, name, cls.oid_suf)

    @classmethod
    def to_raw_name(cls, fas_name):
        """
        Extracts name from FAS openId identifier
        :param str fas_name: FAS user openId
        :return str: user raw name
        """
        if fas_name.startswith(cls.oid_pre) and fas_name.endswith(cls.oid_suf):
            return fas_name.replace(cls.oid_pre, "").replace(cls.oid_suf, "")
        else:
            raise Exception("Malformed fas name: `{}`".format(fas_name))


@app.before_request
def lookup_current_user():
    g.user = None
    if 'openid' in session:
        username = FasOID.to_raw_name(session['openid'])
        g.user = User.query.filter_by(username=username).first()


@auth_bp.route('/login', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None:
        session["openid_attempts"] = 0
        print("\n\n\n LOGGED IN \n\n\n\n")
        return redirect(oid.get_next_url())
    else:
        openid_attempts_count = session.get("openid_attempts", 0)
        if openid_attempts_count > 300:
            raise Exception("OpenID auth failed to much times")
        else:
            session["openid_attempts"] = openid_attempts_count + 1
            return oid.try_login(FasOID.uri,
                                 ask_for=['email', 'timezone'],)


@oid.after_login
def create_or_login(resp):
    session['openid'] = resp.identity_url
    username = FasOID.to_raw_name(resp.identity_url)
    user = User.query.filter_by(username=username).first()
    if user is not None:
        flash(u'Successfully signed in')
        g.user = user
    else:

        # ToDo: create auth_logic and move it there
        user = User(
            username=username,
            mail=resp.email,
            timezone=resp.timezone)
        db.session.add(user)
        db.session.commit()

    return redirect(oid.get_next_url())


@auth_bp.route("/logout/")
def logout():
    flask.session.pop("openid", None)
    flask.flash(u"You were signed out")
    return flask.redirect(oid.get_next_url())
