# coding: utf-8
import json
import random
import os
import time
import subprocess
import pipes
import logging

from urllib.parse import urljoin

from dateutil.parser import parse as dt_parse
import requests

from .. import app
from ..exceptions import DockerHubCreateRepoError, DockerHubQueryError

log = logging.getLogger(__name__)

logging.getLogger("requests").setLevel(logging.WARN)


def get_builds_history(repo_name: str) -> "List[dict]":
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
            created_on=dt_parse(build_dict["created_on"]),
            updated_on=dt_parse(build_dict["updated_on"])
        )
    try:
        return [fix_date(b) for b in json.loads(std_out)]
    except (ValueError, KeyError):
        raise DockerHubQueryError(msg="Failed to parse casperjs respons: `{}` after cmd: `{}`"
                                  .format(std_out, " ".join(cmd)))


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
        src_dir,  "../../../phantom/dockerhub_create.js"))

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
