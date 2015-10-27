# coding: utf-8

from flask_wtf import Form
from wtforms import StringField, ValidationError


class CoprSearchLinkForm(Form):
    query = StringField(label="Search for copr projects")


class CoprNameValidator(object):
    def __init__(self, message=None):
        if not message:
            message = "Wrong format for copr name: '{}'"
        self.message = message

    def __call__(self, form, field):
        try:
            user, copr = field.data.split("/")
            if not user:
                raise ValidationError("Missing copr username")
            if not copr:
                raise ValidationError("Missing copr projectname")
        except ValueError:
            raise ValidationError(self.message.format(field.data))


class CoprLinkAddForm(Form):
    copr_name = StringField(label="Enter copr in the format `copr_owner/copr_project`",
                            validators=[CoprNameValidator()])
