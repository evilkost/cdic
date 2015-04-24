# coding: utf-8

from flask_wtf import Form, RecaptchaField
from wtforms import StringField, PasswordField, BooleanField, RadioField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Email
from wtforms.fields.html5 import URLField


class CoprSearchLinkForm(Form):
    # TODO: add input validation

    query = StringField(label="Search for copr projects")
    copr_name = StringField(label="Enter copr in the format `copr_owner/copr_project`")
