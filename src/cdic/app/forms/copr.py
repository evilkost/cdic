# coding: utf-8

from flask_wtf import Form
from wtforms import StringField


class CoprSearchLinkForm(Form):
    # TODO: add input validation

    query = StringField(label="Search for copr projects")
    copr_name = StringField(label="Enter copr in the format `copr_owner/copr_project`")
