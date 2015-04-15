# coding: utf-8

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap



app = Flask(__name__)

# oid = OpenID(app, app.config["OPENID_STORE"], safe_roots=[])
app.config.from_pyfile("../config.py")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
Bootstrap(app)

db = SQLAlchemy()
db.init_app(app)


from .views.main import main_bp
from .views.auth import auth_bp

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
