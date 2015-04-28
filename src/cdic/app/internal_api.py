# coding: utf-8

"""
Expose operations with cdic db to local scripts
"""

from sqlalchemy.sql import true, false

from . import app, db
from .models import User, Project
from .logic.project_logic import get_project_by_id
from .logic.event_logic import create_project_event


class Api(object):

    @staticmethod
    def get_pending_github_create_repo_list() -> "Iterable[Project]":
        """
        :return: iterable of Project
        """
        return (Project.query
                .filter(Project.build_is_running == true())  # don't create repo
                                                             # until first build
                .filter(Project.github_repo_exists == false()))


    @staticmethod
    def set_github_repo_created(ident: int):
        prj = get_project_by_id(ident)
        prj.github_repo_exists = True

        pe = create_project_event(prj, "Created github repo")
        db.session.add_all([prj, pe])
        db.session.commit()

    @staticmethod
    def get_pending_docker_create_repo_list() -> "Iterable[Project]":
        return (
            Project.query
            .filter(Project.github_repo_exists == true())
            .filter(Project.dockerhub_repo_exists == false())
        )

    @staticmethod
    def get_config():
        return app.config

    @staticmethod
    def set_docker_repo_created(ident: int):
        prj = get_project_by_id(ident)
        prj.dockerhub_repo_exists = True

        pe = create_project_event(prj, "Created dockerhub automated build")
        db.session.add_all([prj, pe])
        db.session.commit()
