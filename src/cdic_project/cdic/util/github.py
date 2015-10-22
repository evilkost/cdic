# coding: utf-8

import json
import logging

from requests import request

from .. import app

log = logging.getLogger(__name__)


class GhClient(object):

    def __init__(self,):
        self.api_root = app.config["GITHUB_API_ROOT"]
        self.user = app.config["GITHUB_USER"]
        self.token = app.config["GITHUB_TOKEN"]

    def do_auth_request(self, url, data=None, method=None):
        method = method or "get"
        headers = {"Authorization": "token {}".format(self.token)}
        return request(method=method, url=url, data=data, headers=headers)

    def create_repo(self, repo_name):
        response = self.do_auth_request(
            url="{}/user/repos".format(self.api_root),
            data=json.dumps({"name": repo_name}),
            method="post",
        )
        log.info("< {}".format(response))
        # TODO: check response code

    def delete_repo(self, repo_name):
        response = self.do_auth_request(
            url="{}/repos/{}/{}".format(self.api_root, self.user, repo_name),
            method="delete"
        )
        log.info("< {}".format(response))



# def create_github_repo(api, *args, **kwargs):
#     client = GhClient(api.get_config())
#     created_list = []
#
#     for project in api.get_pending_github_create_repo_list():
#         repo_name = project.repo_name
#         try:
#             log.info("Creating repo: {}".format(repo_name))
#             client.create_repo(repo_name)
#             created_list.append(repo_name)
#             api.set_github_repo_created(project.id)
#         except Exception as err:
#             log.exception(err)
#     else:
#         log.debug("No projects to create github repo")


def reschedule_unfinished_jobs(api, *args, **kwargs):
    for project in api.get_pending_github_create_repo_list():
        repo_name = project.repo_name
