# coding: utf-8

from abc import ABCMeta
import datetime
import json
import os
from tempfile import NamedTemporaryFile
import subprocess
import pipes
import logging

from backports.typing import Iterable
from dateutil.parser import parse as dt_parse
from requests import get
from lxml import html

from ..exceptions import DockerHubQueryError

log = logging.getLogger(__name__)

logging.getLogger("requests").setLevel(logging.WARN)


class BuildInfo(object):

    def __init__(self, info_table: dict, logs: str):
        self.info_table = info_table
        self.logs = logs

        self._created_at = None

    def parse_created_at(self):
        raw_str = self.info_table.get("created_at")
        if raw_str:
            try:
                cleaned_str = raw_str.split("(")[1].split(")")[0]
                self._created_at = dt_parse(cleaned_str)

            except Exception:
                log.exception("Failed to parse created_at: {}".format(raw_str))

    @property
    def created_at(self) -> datetime:
        if self._created_at is None:
            self.parse_created_at()

        return self._created_at

    @property
    def error(self):
        return self.info_table.get("error")


class BuildStatus(object):

    def __init__(self, repo_name, build_id, href, status):
        self.repo_name = repo_name
        self.build_id = build_id
        self.href = href
        self.status = status

    def __str__(self):
        return "<BS: {} id: {}, status: {}>".format(self.repo_name, self.build_id, self.status)


    class ScriptResult(object):

        def __init__(self, is_ok: bool, data: dict=None):
            self.is_ok = is_ok
            self.data = data


class AbstractDhConnector(metaclass=ABCMeta):

    def get_build_info(self, repo_name: str, build_id: str) -> BuildInfo or None:
        pass

    def create_project(self, repo_name: str) -> bool:
        pass

    def delete_project(self, repo_name: str) -> bool:
        pass

    def get_build_trigger_url(self, repo_name: str) -> str or None:
        pass

    def fetch_builds_status(self, repo_name: str) -> Iterable[BuildStatus]:
        pass


class ScriptResult(object):

    def __init__(self, is_ok: bool, data: dict=None):
        self.is_ok = is_ok
        self.data = data


class ScriptDriver(metaclass=ABCMeta):
    def run_script(self, script_name: str, options: dict) -> ScriptResult:
        pass


class CasperJsScriptDriver(ScriptDriver):

    def __init__(self, opts):
        """
        :param dict opts: Dict with the following keys:

            *VAR_ROOT* location to store runtime data
            *DOCKERHUB_USERNAME*
            *DOCKERHUB_PASSWORD*
            *GITHUB_USER*

        """
        self.opts = opts

    def run_script(self, script_name: str, options: dict) -> ScriptResult:
        credentionals, script_path = self.prepare_script(script_name)
        with NamedTemporaryFile() as result_file:
            save_to = result_file.name

            cmd = [
                "/usr/bin/xvfb-run",
                "/usr/local/bin/casperjs",  # TODO: move to config
                "--engine=slimerjs",
                script_path,
                "--save_to={}".format(save_to),
                "--credentials={}".format(pipes.quote(credentionals)),
            ]
            for k, v in options.items():
                cmd.append("--{}={}".format(k, v))
            try:
                log.debug("Executing:\n{}".format(" ".join(cmd)))
                subprocess.call(cmd)
                content = result_file.read().decode()
                result = json.loads(content)
                return ScriptResult(True, result)
            except Exception:
                log.exception("Failed to execute cmd: {}".format(cmd))
                return ScriptResult(False, None)

    def prepare_script(self, script_name):
        credentionals = os.path.join(self.opts["VAR_ROOT"],
                                     "dockerhub_credentionals.json")
        if not os.path.exists(credentionals):
            with open(credentionals, "w") as handle:
                handle.write(json.dumps({
                    "username": self.opts["DOCKERHUB_USERNAME"],
                    "password": self.opts["DOCKERHUB_PASSWORD"],
                    "github_username": self.opts["GITHUB_USER"],
                }))
        src_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.abspath(os.path.join(
            src_dir, "../../../phantom/{}".format(script_name)))
        return credentionals, script_path


class DhConnector(AbstractDhConnector):

    def __init__(self, opts, script_driver=None):
        """
        :param dict opts: Dict with the following keys:

            *VAR_ROOT* location to store runtime data
            *DOCKERHUB_USERNAME*
            *DOCKERHUB_PASSWORD*
            *GITHUB_USER*
        :type script_driver: ScriptDriver
        """

        self.opts = opts
        self.driver = script_driver or CasperJsScriptDriver(opts)

    def get_build_info(self, repo_name: str, build_id: str) -> BuildInfo or None:
        log.info("Getting build info from dockerhub")
        result = self.driver.run_script(
            "get_build_info.js", {"repo_name": repo_name, "build_id": build_id})

        if result.is_ok and "info_table" in result.data and "logs" in result.data:
            return BuildInfo(result.data["info_table"], result.data["logs"])

        return None

    def create_project(self, repo_name) -> bool:
        """
        :return: True on successful creation, False otherwise
        """
        log.info("Creating automated project: {}".format(repo_name))
        result = self.driver.run_script("create_project.js", {"repo_name": repo_name})
        if result.is_ok and result.data["status"] == "created":
            return True

        return False

    def delete_project(self, repo_name) -> bool:
        """
        :return: True on successful deletion, False otherwise
        """
        log.info("Deleting repo: {}".format(repo_name))
        result = self.driver.run_script("delete_project.js", {"repo_name": repo_name})
        if result.is_ok and result.data["status"] == "deleted":
            return True
        else:
            return False

    def get_build_trigger_url(self, repo_name: str) -> str or None:
        log.info("Getting build trigger url: {}".format(repo_name))
        result = self.driver.run_script("get_build_trigger.js", {"repo_name": repo_name})
        if result.is_ok:
            return result.data["trigger_url"]
        else:
            raise DockerHubQueryError(msg="Unable to get trigger url for project `{}`".format(repo_name))

    def fetch_builds_status(self, repo_name: str) -> Iterable[BuildStatus]:
        url = "https://hub.docker.com/r/{}/{}/builds/".format(
            self.opts["DOCKERHUB_USERNAME"], repo_name)
        raw = get(url)

        tree = html.fromstring(raw.text)
        rows = tree.xpath("//table//tbody//tr")
        result = []
        for row in rows:
            children = row.getchildren()
            log.error(children)
            try:
                b_elem = children[0].xpath(".//a")[0]

                href = b_elem.attrib["href"]
                build_id = b_elem.text_content()
                status = children[0].text_content()

                bs = BuildStatus(repo_name, build_id, href, status)
                result.append(bs)

            except Exception as e:
                log.exception("Failed to parse row")

        return result
