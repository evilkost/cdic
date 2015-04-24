# coding: utf-8

"""
Expose operations with cdic db to local scripts
"""

from sqlalchemy.sql import true, false

from . import app, db
from .models import User, Project
from .logic.project_logic import get_project_by_id


class Api(object):

    @staticmethod
    def get_pending_github_create_repo_list() -> "Iterable[Project]":
        """
        :return: iterable of Project
        """
        return Project.query.filter(Project.github_repo_exists == false())


    @staticmethod
    def set_github_repo_created(ident: int):
        prj = get_project_by_id(ident)
        prj.github_repo_exists = True
        db.session.add(prj)
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
        db.session.add(prj)
        db.session.commit()
