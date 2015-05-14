# coding: utf-8

import json
import logging

from requests import request


log = logging.getLogger(__name__)


class GhClient(object):

    def __init__(self, app_config):
        self.api_root = app_config["GITHUB_API_ROOT"]
        self.user = app_config["GITHUB_USER"]
        self.token = app_config["GITHUB_TOKEN"]

    def do_auth_request(self, url, data=None, method=None):
        method = method or "get"
        headers = {"Authorization": "token {}".format(self.token)}
        return request(method=method, url=url, data=data, headers=headers)

    def create_repo(self, title):
        response = self.do_auth_request(
            url="{}/user/repos".format(self.api_root),
            data=json.dumps({"name": title}),
            method="post",
        )
        log.info("< {}".format(response))
        # TODO: check response code





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
