# coding: utf-8

import os
import sys
import logging
from flask import Flask, jsonify, render_template, url_for
import flask
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.utils import redirect

from .exceptions import AccessRejected
from .util.git import GitStore
from .util.dockerhub import DhConnector

app = Flask(__name__)

# oid = OpenID(app, app.config["OPENID_STORE"], safe_roots=[])
app.config.from_pyfile("../config.py")
app.config.from_pyfile("/etc/cdic/cdic_db.py", silent=True)
app.config.from_pyfile(os.path.expanduser("~/.config/cdic.py"), silent=True)

log = logging.getLogger(__name__)

Bootstrap(app)

git_store = GitStore(app.config["CDIC_WORKPLACE"])

db = SQLAlchemy()
db.init_app(app)

app.dh_connector = DhConnector(app.config)
""":type:cdic_project.cdic.util.DhConnector"""

from .filters import time_ago

from .views.main import main_bp
from .views.auth import auth_bp
from .views.project import project_bp

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(project_bp)


@app.route('/api/help', methods=['GET'])
def help_urls():
    """Print available functions."""
    func_list = {}
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            func_list[rule.rule] = app.view_functions[rule.endpoint].__doc__
    return jsonify(func_list)


@app.errorhandler(NoResultFound)
def page_not_found(error):
    flask.flash("requested page not found: {}".format(flask.request.path), "danger")
    return redirect(url_for("main.index"))


@app.errorhandler(404)
def page_not_found(error):
    flask.flash("requested page not found: {}".format(flask.request.path), "danger")
    return redirect(url_for("main.index"))


if __name__ == "__main__":
    logging.basicConfig(
        filename=app.config["MAIN_LOG"],
        format='[%(asctime)s][%(threadName)10s][%(levelname)6s][%(name)s]: %(message)s',
        level=logging.DEBUG
    )


@app.errorhandler(AccessRejected)
def access_rejected_handler(error):
    flask.flash(str(error), "danger")
    return redirect(url_for("main.index"))



