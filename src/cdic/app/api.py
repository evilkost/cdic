# coding: utf-8


"""
Expose operations with cdic db to local scripts
"""

from . import app, db
from .models import User, Project


class Api(object):

    @staticmethod
    def get_pending_github_create_repo():
        return ["foobar-2"]

    @staticmethod
    def set_github_repo_created(repo_name_list):
        print(repo_name_list)
        pass

    @staticmethod
    def get_pending_docker_create_repo():
        """
        select project names with:
            1. dockerhub_repo_created == False
            2. github_repo_created == True
        :return: list of
        """
        return ["cdic_test_02", "foobar"]

    @staticmethod
    def get_config():
        return app.config

    @staticmethod
    def set_docker_repo_created(repo_name_list):
        print(repo_name_list)
        pass
