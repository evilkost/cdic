# coding: utf-8

from flask import g
from flask_wtf import Form
from wtforms import StringField, RadioField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Regexp
from wtforms.fields.html5 import URLField
from app.models import Project

from ..logic.project_logic import exists_for_user
from ..constants import SourceType


# todo: custom validation for git_url presence when this mode is selected


class ProjectUniqueNameValidator(object):

    def __init__(self, message=None):
        if not message:
            message = "You already have project named '{}'."
        self.message = message

    def __call__(self, form, field):
        existing = exists_for_user(g.user, field.data)
        if existing:
            raise ValidationError(self.message.format(field.data))


class ExistingRepoNameValidator(object):
    # since we use - as delimiter between user name and project title
    # one could forge a new user so that resulting repo_name would be equal to existing repo
    # i.e. assume there is a user `foo` with project `bar-xyz`, than attacker creates
    # account `foo-bar`
    def __init__(self, message=None):
        if not message:
            message = "You title conflicts with existing repo '{}'."
        self.message = message


class ProjectForm(Form):
    local_text = TextAreaField()

    git_url = URLField("Git source url")
    dockerfile_path = StringField()


class ProjectCreateForm(Form):

    title = StringField("Project title", [
        DataRequired(),
        Regexp(r'^[\w|\d|-]+$', message="Title should contains only numbers, letters or `-`"),
        ProjectUniqueNameValidator()
    ])

    source_mode = RadioField(SourceType.LOCAL_TEXT,
                             choices=[(x, x.replace("_", " ").capitalize()) for x in SourceType.get_all_options()],
                             default=SourceType.LOCAL_TEXT)

class SameTextValidator(object):

    def __init__(self, message=None, value=None):
        if not message:
            message = "Field value should be equal to " + str(value) + " not {}."
        self.message = message
        self.value = value

    def __call__(self, form, field):
        if field.data != self.value:
            raise ValidationError(self.message.format(field.data))


def delete_form_factory(project: Project) -> Form:

    class DeleteProjectForm(Form):

        mb_title = StringField("Please enter project title to confirm your intention", [
            DataRequired(),
            SameTextValidator(message="Please repeat project title, `{}` is a wrong one",
                              value=project.title)
        ])

    return DeleteProjectForm()
