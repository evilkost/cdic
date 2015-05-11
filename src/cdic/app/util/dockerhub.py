# coding: utf-8

import sys
import time

from functools import partial
import logging

from urllib.parse import urljoin
from dateutil.parser import parse as dt_parse


from robobrowser import RoboBrowser

log = logging.getLogger(__name__)

logging.getLogger("requests").setLevel(logging.WARN)

#
#
# class MechanizeProvider(object):
#     """
#     Need this, to be able replace RoboBrowser if needed
#     """
#
#     def __init__(self, timeout, retries):
#         self.timeout = timeout
#         self.retries = retries
#
#     def open_url(self, url):
#         pass
#
#     def open_link_by_text(self, text):
#         """
#         Should find a link (tag <a>) with given text and go to it
#         """
#         pass
#
#     def reset_browser(self):
#         pass
#
#     def get_status(self) -> int:
#         pass
#
#     def find_and_fill_form(self, url: str, form_id: str, form_fields: dict):
#         """
#         :param dict form_fields: field_name -> value
#         """
#         pass


# class RBP(MechanizeProvider):
class RBP(object):

    def __init__(self,  timeout=10, retries=1):
        self.timeout = timeout
        self.retries = retries

        self.browser = None
        self.reset_browser()

    def reset_browser(self):
        self.browser = RoboBrowser(
            history=True, timeout=self.timeout,
            tries=self.retries + 1,  # rb bug
            allow_redirects=False
            # allow_redirects=True
        )
        log.info("Got new RB instance")

    def open_url(self, url):
        log.info("< trying to open: {}".format(url))
        self.browser.open(url)
        log.info("> {}".format(self.browser.response.status_code))
        self.follow_redirect()

    def open_link_by_text(self, text):
        try:
            a = self.browser.get_link(text)
            path = a.attrs["href"]
            go_to = urljoin(self.browser.url, path)
            self.open_url(go_to)
        except Exception:
            log.exception("Failed to find a link with text: {}".format(text))
            raise

    def follow_redirect(self):
        if self.status in [301, 302]:
            redir_to = self.browser.response.headers["Location"]
            log.debug("response headers: \n{}".format(self.browser.response.headers))
            log.info("Following redirect: {}".format(redir_to))
            self.insert_referer()
            self.open_url(redir_to)

    @property
    def status(self):
        return self.get_status()

    def get_status(self):
        return self.browser.response.status_code

    def insert_referer(self):
        self.browser.session.headers["Referer"] = self.browser.url

    def find_and_fill_form(self, url, form_id, form_fields):
        log.info("< opening login page: {}".format(url))
        self.browser.open(url)
        log.info("> {}".format(self.browser.response.status_code))
        self.follow_redirect()

        form = self.browser.get_form(id=form_id)
        for field_name, value in form_fields.items():
            form[field_name].value = value

        self.insert_referer()
        log.info("< submitting  form: {}".format(form))
        self.browser.submit_form(form)
        log.info("> {}".format(self.browser.response.status_code))
        self.follow_redirect()


# def mp_fabric(name, *args, **kwargs) -> MechanizeProvider:
#     klass = None
#     if name == "RoboBrowser":
#         klass = RBP
#
#     if klass is None:
#         raise NotImplementedError("RBP `{}` not implemented yet".format(name))
#     else:
#         return klass(*args, **kwargs)


class Creator(object):

    SLEEP_TIME = 2
    MAX_TRIES = 100

    def __init__(self, app_config, build_name_list):
        self.timeout = 10
        self.tries = 3

        self.br = RBP(timeout=self.timeout, retries=self.tries)

        self.username = app_config["DOCKERHUB_USERNAME"]
        self.password = app_config["DOCKERHUB_PASSWORD"]
        self.dh_url = app_config["DOCKERHUB_URL"]
        self.dr_url = app_config["DOCKERREGISTRY_URL"]
        self.login_url = "{}/account/login/".format(self.dh_url)
        self.github_repo_name = app_config["GITHUB_USER"]

        self.ac_creation_url_tpl = "{dr_url}/builds/github/{github_repo_name}/{build_name}/"

        self.build_name_list = build_name_list
        self.stage_num = 0
        self.tries_done = 0
        self.stages = [
            self.do_login,
            partial(self.br.open_url, "{}/builds/add/".format(self.dr_url)),
            partial(self.br.open_url, "{}/builds/github/select/".format(self.dr_url)),
        ]
        self.stages.extend([
            partial(self.submit_create, bn) for bn in self.build_name_list
        ])

        self.create_done_list = []

    def do_login(self):
        self.br.reset_browser()
        self.br.find_and_fill_form(self.login_url, form_id="form-login",
                                   form_fields={"username": self.username, "password": self.password})

    def submit_create(self, build_name):
        if build_name in self.create_done_list:
            # skip on re-run
            return

        url = self.ac_creation_url_tpl.format(
            dr_url=self.dr_url,
            github_repo_name=self.github_repo_name,
            build_name=build_name)
        self.br.find_and_fill_form(url, form_id="mainform", form_fields={})
        if self.br.get_status() == 200:
            self.create_done_list.append(build_name)

    def do_next_stage(self):
        stage = self.stages[self.stage_num]
        log.debug("Doing stage: #{}".format(self.stage_num))
        time.sleep(self.SLEEP_TIME)
        try:
            stage()
            self.stage_num += 1
        except Exception as err:
            log.exception(err)
            self.stage_num = 0
            self.tries_done += 1

    def run(self):
        while self.tries_done < self.MAX_TRIES:
            if self.stage_num == len(self.stages):
                break
            else:
                self.do_next_stage()
        else:
            log.error("Failed to create")

        return self.create_done_list


def get_builds_history(api, repo_name: str):
    config = api.get_config()
    br = RBP()

    start_url = config["HUB_PROJECT_URL_TEMPLATE"].format(repo_name=repo_name)

    br.open_url(start_url)
    br.open_link_by_text("Build Details")
    page = br.browser
    table = page.find(text="Builds History").next

    builds = []
    for row in table.find_all("tr")[1:]:
        fields = dict(enumerate(row.find_all("td")))
        build = {
            "build_id": fields[0].text,
            "status": fields[1].text,
            "created_on": dt_parse(fields[2].attrs["utc-date"]),
            "updated_on": dt_parse(fields[3].attrs["utc-date"]),
        }
        builds.append(build)
    return builds


def add_webhook():
    # TODO: implement
    pass


def create_pending_dockerhub(api):
    """
    :param api: Api to cdic service, see cdic.app.api:Api class
    :type: ..app.api.Api
    """
    projects_list = api.get_pending_docker_create_repo_list()
    repo_name_list = list([prj.repo_name for prj in projects_list])
    if not repo_name_list:
        log.debug("No projects to create docker hub repo")
        return

    log.info("create_pending_repo invoked, pending:{}"
             .format(repo_name_list))

    creator = Creator(api.get_config(), repo_name_list)
    created_repo_list = creator.run()

    name_to_project_id = {prj.repo_name: prj.id for prj in projects_list }
    for name in created_repo_list:
        api.set_docker_repo_created(name_to_project_id[name])
