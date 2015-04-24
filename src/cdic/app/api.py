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
    def get_pending_github_create_repo() -> "List[Project]":
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
    def get_pending_docker_create_repo():
        """
        select project names with:
            1. dockerhub_repo_created == False
            2. github_repo_created == True
        :return: list of tuples (primary key, repo title)
        """
        return ["cdic_test_02", "foobar"]

    @staticmethod
    def get_config():
        return app.config

    @staticmethod
    def set_docker_repo_created(repo_name_list):
        print(repo_name_list)
        pass
