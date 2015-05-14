# coding: utf-8

from sqlalchemy.sql import true, false

from .. import db
from ..models import Project

from .project_logic import get_project_by_id
from .event_logic import create_project_event


def get_pending_github_create_repo_list() -> "Iterable[Project]":
    """
    :return: iterable of Project
    """
    return (Project.query
            .filter(Project.build_is_running == true())  # don't create repo
                                                         # until first build
            .filter(Project.github_repo_exists == false()))


def set_github_repo_created(project: Project):
    if not project.github_repo_exists:
        project.github_repo_exists = True

        pe = create_project_event(project, "Created github repo")
        db.session.add_all([project, pe])
        db.session.commit()
