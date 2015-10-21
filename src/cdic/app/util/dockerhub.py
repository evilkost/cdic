# coding: utf-8
import datetime
import json
import random
import os
from tempfile import NamedTemporaryFile
import time
import subprocess
import pipes
import logging

from urllib.parse import urljoin


from backports.typing import List, Iterable

from dateutil.parser import parse as dt_parse
import pytz
import requests
from requests import get
from lxml import html

from .. import app
from ..exceptions import DockerHubCreateRepoError, DockerHubQueryError

log = logging.getLogger(__name__)

logging.getLogger("requests").setLevel(logging.WARN)


def dt_parse_to_utc_without_tz(val: str) -> datetime.datetime:
    tz = pytz.timezone("UTC")
    return dt_parse(val).astimezone(tz).replace(tzinfo=None)


def get_builds_history(repo_name: str) -> List[dict]:
    """
    :param repo_name:
    :raises DockerHubQueryError: If failed to execute query script or got mall formed result
    """
    src_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.abspath(os.path.join(
        src_dir,  "../../../phantom/get_build_history.js"))

    cmd = [
        "/usr/bin/casperjs",
        "--repo_name={}".format(pipes.quote(repo_name)),
        "--dockerhub_user={}".format(app.config["DOCKERHUB_USERNAME"]),
        script_path
    ]
    log.debug("Executing:\n{}".format(" ".join(cmd)))

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = map(lambda x: x.decode("utf-8"), p.communicate())

    if p.returncode != 0:
        raise DockerHubQueryError(msg="Casperjs command failed.: {}".format(" ".join(cmd)),
                                  return_code=p.returncode, stdout=std_out, stderr=std_err)
    else:
        log.debug("STDOUT: \n" + std_out)

    def fix_date(build_dict):
        return dict(
            build_id=build_dict["build_id"],
            status=build_dict["status"],
            created_on=dt_parse_to_utc_without_tz(build_dict["created_on"]),
            updated_on=dt_parse_to_utc_without_tz(build_dict["updated_on"])
        )
    try:
        return [fix_date(b) for b in json.loads(std_out)]
    except (ValueError, KeyError):
        raise DockerHubQueryError(msg="Failed to parse casperjs respons: `{}` after cmd: `{}`"
                                  .format(std_out, " ".join(cmd)))

def run_dockerhub_build(repo_name):
    """
    Run existing automated build
    :raises DockerHubQueryError: when failed to run build
    """

    # todo add project.dh_run_build_sent_on_local_time
    log.info("Sending request for the new build: {}".format(repo_name))
    # ensure that credentials file for casperjs exists,
    # todo: generalize functions
    credentionals, script_path = prepare_casperjs_script("run_build.js")

    cmd = [
        "/usr/bin/casperjs",
        "--repo_name={}".format(pipes.quote(repo_name)),
        "--credentials={}".format(pipes.quote(credentionals)),
        script_path
    ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = map(lambda x: x.decode("utf-8"), p.communicate())

    if p.returncode != 0:
        raise DockerHubQueryError(msg="Casperjs command failed.: {}".format(" ".join(cmd)),
                                  return_code=p.returncode, stdout=std_out, stderr=std_err)
    else:
        log.debug("STDOUT: \n" + std_out)


def create_dockerhub_automated_build_repo(repo_name):
    """
    Create new automated build at dockerhub using phantomjs/casperjs
    This function is rather time consuming, expect 15secons on average

    :param repo_name:
    :return: Nothing on success
    :raises DockerHubCreateRepoError: when failed to create automated build
    """
    log.info("Creating new automated build: {}".format(repo_name))
    # ensure that credentials file for casperjs exists
    credentionals, script_path = prepare_casperjs_script("dockerhub_create.js")

    cmd = [
        "/usr/bin/casperjs",
        "--repo_name={}".format(pipes.quote(repo_name)),
        "--credentials={}".format(pipes.quote(credentionals)),
        script_path
    ]
    log.debug("Executing:\n{}".format(" ".join(cmd)))

    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = map(lambda x: x.decode("utf-8"), p.communicate())

    if p.returncode != 0:
        raise DockerHubCreateRepoError(msg="Casperjs command failed.: {}".format(" ".join(cmd)),
                                       return_code=p.returncode, stdout=std_out, stderr=std_err)
    else:
        log.debug("STDOUT: \n" + std_out)

    # now we need to check that repo was really created,
    # because dockerhub returns 200 even if it fails to create new repo
    url = 'https://registry.hub.docker.com/u/' + app.config["DOCKERHUB_USERNAME"] + '/' + repo_name
    log.debug("check that repo was created at: {}".format(url))
    response = requests.get(url)
    log.info(response)
    if response.status_code != 200:
        raise DockerHubCreateRepoError(msg="Repo doesn't exists at `{}`".format(url))

    log.info("Finished creation of new dockerhub repo: {}".format(repo_name))


def delete_dockerhub(repo_name):
    log.info("Deleting repo: {}".format(repo_name))
    credentionals, script_path = prepare_casperjs_script("dockerhub_delete.js")

    cmd = [
        "/usr/bin/casperjs",
        "--repo_name={}".format(pipes.quote(repo_name)),
        "--credentials={}".format(pipes.quote(credentionals)),
        script_path
    ]
    log.debug("Executing:\n{}".format(" ".join(cmd)))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std_out, std_err = map(lambda x: x.decode("utf-8"), p.communicate())

    if p.returncode != 0:
        log.error("Casperjs command failed.: {}\n return code: {}, stdout: {}, stderr: {}"
                  .format(" ".join(cmd), p.returncode, std_out, std_err))
    else:
        log.debug("STDOUT: \n" + std_out)

    # need to ensure that dh build actually vanished
    url = 'https://registry.hub.docker.com/u/' + app.config["DOCKERHUB_USERNAME"] + '/' + repo_name
    log.debug("check that repo was vanished from: {}".format(url))
    response = requests.get(url)
    log.info(response)
    if response.status_code == 200:
        raise DockerHubQueryError(msg="Repo still exists at `{}`".format(url))

    log.info("Finished deletion of dockerhub repo: {}".format(repo_name))


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


def get_build_info(repo_name: str, build_id: str) -> BuildInfo or None:
    log.info("Getting build info from dockerhub")
    result = run_casperjs_script("get_build_info.js",
                                 {"repo_name": repo_name,
                                  "build_id": build_id})

    if result.is_ok and "info_table" in result.data and "logs" in result.data:
        return BuildInfo(result.data["info_table"], result.data["logs"])

    return None


def create_project(repo_name) -> bool:
    """
    :return: True on successful creation, False otherwise
    """
    log.info("Creating automated project: {}".format(repo_name))
    result = run_casperjs_script("create_project.js", {"repo_name": repo_name})
    if result.is_ok and result.data["status"] == "created":
        return True

    return False


def delete_project(repo_name) -> bool:
    """
    :return: True on successful deletion, False otherwise
    """
    log.info("Deleting repo: {}".format(repo_name))
    result = run_casperjs_script("delete_project.js", {"repo_name": repo_name})
    if result.is_ok and result.data["status"] == "deleted":
        return True
    else:
        return False


def get_build_trigger_url(repo_name: str) -> str or None:
    log.info("Getting build trigger url: {}".format(repo_name))
    result = run_casperjs_script("get_build_trigger.js", {"repo_name": repo_name})
    if result.is_ok:
        return result.data["trigger_url"]
    else:
        raise DockerHubQueryError(msg="Unable to get trigger url for project `{}`".format(repo_name))


class ScriptResult(object):

    def __init__(self, is_ok: bool, data: dict=None):
        self.is_ok = is_ok
        self.data = data


def run_casperjs_script(script_name: str, options: dict) -> ScriptResult:
    credentionals, script_path = prepare_casperjs_script(script_name)
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


def prepare_casperjs_script(script_name):
    credentionals = os.path.join(app.config["VAR_ROOT"], "dockerhub_credentionals.json")
    if not os.path.exists(credentionals):
        with open(credentionals, "w") as handle:
            handle.write(json.dumps({
                "username": app.config["DOCKERHUB_USERNAME"],
                "password": app.config["DOCKERHUB_PASSWORD"],
                "github_username": app.config["GITHUB_USER"],
            }))
    src_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.abspath(os.path.join(
        src_dir, "../../../phantom/{}".format(script_name)))
    return credentionals, script_path


class BuildStatus(object):

    def __init__(self, repo_name, build_id, href, status):
        self.repo_name = repo_name
        self.build_id = build_id
        self.href = href
        self.status = status

    def __str__(self):
        return "<BS: {} id: {}, status: {}>".format(self.repo_name, self.build_id, self.status)


def fetch_build_status_fast(repo_name: str) -> Iterable[BuildStatus]:
    url = "https://hub.docker.com/r/{}/{}/builds/".format(
        app.config["DOCKERHUB_USERNAME"], repo_name)
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
