# coding: utf-8

from .. import db
from ..models import Project

from .event_logic import create_project_event


def set_github_repo_created(project: Project):
    if not project.github_repo_exists:
        project.github_repo_exists = True

        pe = create_project_event(project, "Created github repo")
        db.session.add_all([project, pe])
        db.session.commit()
