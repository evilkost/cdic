# coding: utf-8

from flask_wtf import Form, RecaptchaField
from wtforms import StringField, PasswordField, BooleanField, RadioField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Email
from wtforms.fields.html5 import URLField

from ..constants import SourceType

# todo: custom validation for git_url presence when this mode is selected


class ProjectForm(Form):

    title = StringField("Project title", [DataRequired()])

    source_mode = RadioField(SourceType.LOCAL_TEXT,
                             choices=[(x, x.replace("_", " ").capitalize()) for x in SourceType.get_all_options()],
                             default=SourceType.LOCAL_TEXT)

    local_text = TextAreaField()

    git_url = URLField("Git source url")
    dockerfile_path = StringField()
