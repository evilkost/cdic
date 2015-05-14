# coding: utf-8
import random

import sys
import time

from functools import partial
import logging

from urllib.parse import urljoin
from dateutil.parser import parse as dt_parse


from robobrowser import RoboBrowser
import mechanicalsoup


from .. import app
import robobrowser
from ..logic.dockerhub_logic import get_pending_docker_create_repo_list, \
    set_docker_repo_created

log = logging.getLogger(__name__)

logging.getLogger("requests").setLevel(logging.WARN)

#


# class MechanizeProvider(object):
#     """
#     Need this, to be able replace RoboBrowser if needed
#     """
#
#     # def __init__(self, timeout, retries):
#     #     self.timeout = timeout
#     #     self.retries = retries
#
#     def open_url(self, url):
#         pass
#
#     def open_link_by_text(self, text):
#         """timeout=10, retries=1
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
#

# class MSP(MechanizeProvider):
#
#     def __init__(self, timeout=10, retries=1):
#
#         self.browser = None
#         self.last_page = None
#
#     def reset_browser(self):
#         self.browser = mechanicalsoup.Browser()
#         self.last_page = None
#
#     def open_url(self, url):
#         if self.last_page:
#             self.browser.session.headers.update({'referer': self.last_page.url})
#
#         self.last_page = self.browser.get(url)
#         return self.last_page
#
#     def get_status(self):
#         if self.last_page is None:
#             raise RuntimeError("No requests were performed to query status")
#         return self.last_page.status_code
#
#     def find_and_fill_form(self, url: str, form_id: str, form_fields: dict):
#         page = self.open_url(url)
#         form = page.soup.select("#{}".format(form_id))[0]
#         return form
#


# class RBP(MechanizeProvider):
class RBP(object):

    def __init__(self,  timeout=10, retries=1):
        self.timeout = timeout
        self.retries = retries

        self.browser = None
        self.reset_browser()

        self.redirect_counter = 0

        self.referer_enabled = True

    def reset_browser(self):
        self.redirect_counter = 0
        self.browser = RoboBrowser(
            history=True, timeout=self.timeout,
            tries=self.retries + 1,  # rb bug
            allow_redirects=False,
            # allow_redirects=True
            user_agent="Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:37.0) Gecko/20100101 Firefox/37.0"
        )
        log.info("Got new RB instance")

    def open_url(self, url):
        log.info("< trying to open: {}".format(url))
        self.insert_referer()
        self.browser.open(url)
        log.debug("< REQUEST HEADERS: \n{}".format(
            "\n".join(" {}\t{}".format(k, v) for k, v in self.browser.response.request.headers.items())
        ))
        log.info("> {}".format(self.browser.response.status_code))
        log.debug("> RESPONSE HEADERS: \n{}".format(
            "\n".join(" {}\t{}".format(k, v) for k, v in self.browser.response.headers.items())
        ))
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
            self.redirect_counter += 1
            if self.redirect_counter > 10:
                raise RuntimeError("Too much redirects")

            time.sleep(random.random() + 0.3)
            redir_to = self.browser.response.headers["Location"]
            log.info("Following redirect: {}".format(redir_to))
            # if "https://registry.hub.docker.com/u/" in redir_to:
            #     log.debug("")

            self.open_url(redir_to)
        else:
            self.redirect_counter = 0

    @property
    def status(self):
        return self.get_status()

    def get_status(self):
        return self.browser.response.status_code

    def insert_referer(self):
        try:
            hasattr(self.browser, "response")
        except robobrowser.exceptions.RoboError:
            return
        if self.browser.response and self.referer_enabled:
            self.browser.session.headers["Referer"] = self.browser.response.url

    def find_and_fill_form(self, url, form_id, form_fields):
        # log.info("< opening login page: {}".format(url))
        # self.browser.open(url)
        self.open_url(url)
        # log.info("> {}".format(self.browser.response.status_code))

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

    def __init__(self, app_config, build_name_list):
        self.timeout = 10
        self.tries = 1

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
            self.go_to_build_add,
            partial(self.br.open_url, "{}/builds/github/select/".format(self.dr_url)),
        ]
        self.stages.extend([
            partial(self.submit_create, bn) for bn in self.build_name_list
        ])

        self.create_done_list = []

    def go_to_build_add(self):
        try:
            self.br.referer_enabled = False
            self.br.browser.session.headers.pop("Referer")
            # self.br.open_url("{}/u/".format(self.dr_url))
            time.sleep(10)  # some magic with dockerhub oauth processing
            self.br.open_url("{}/builds/add/".format(self.dr_url))
        finally:
            self.br.referer_enabled = True

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
        # TODO: add webhook here ???

    def do_next_stage(self):
        stage = self.stages[self.stage_num]
        log.debug("Doing stage: #{}, attempt: #{}".format(self.stage_num, self.tries_done))
        time.sleep(1)
        try:
            stage()
            self.stage_num += 1
        except Exception as err:
            log.exception(err)
            self.stage_num = 0
            self.tries_done += 1

    def run(self):
        while self.tries_done < self.tries:
            if self.stage_num == len(self.stages):
                break
            else:
                self.do_next_stage()
        else:
            log.error("Failed to create")

        return self.create_done_list


def get_builds_history(config, repo_name: str):
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


def create_pending_dockerhub(*args, **kwargs):
    projects_list = get_pending_docker_create_repo_list()
    repo_name_list = list([prj.repo_name for prj in projects_list])
    if not repo_name_list:
        log.debug("No projects to create docker hub repo")
        return

    log.info("create_pending_repo invoked, pending:{}"
             .format(repo_name_list))

    creator = Creator(app.config, repo_name_list)
    created_repo_list = creator.run()

    name_to_project_id = {prj.repo_name: prj.id for prj in projects_list}
    for name in created_repo_list:
        set_docker_repo_created(name_to_project_id[name])
