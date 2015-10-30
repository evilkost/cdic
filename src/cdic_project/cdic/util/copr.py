# coding: utf-8

import json
from logging import getLogger
from requests import get
from typing import Iterable, List

from copr import CoprClient
from copr.client.responses import ProjectWrapper
try:
    from copr.client.exceptions import CoprRequestException
except ImportError:
    from copr.exceptions import CoprRequestException

from .. import app
from ..models import get_copr_url
from ..exceptions import CoprSearchError

log = getLogger(__name__)


def search_coprs(query) -> List[ProjectWrapper]:
    client = CoprClient(copr_url=app.config.get("COPR_BASE_URL"))
    try:
        projects = client.search_projects(query).projects_list
    except CoprRequestException:
        log.exception("Failed to search for {}".format(query))
        raise CoprSearchError("Failed to search for {}".format(query))
    except KeyError:
        raise CoprSearchError("Found nothing for query: {}".format(query))

    if len(projects) == 0:
        raise CoprSearchError("Found nothing for query: {}".format(query))

    for project in projects:
        setattr(project, "copr_url", get_copr_url(project.username, project.projectname))
    return projects
    # search_api_url = "{}/api/coprs/search/{}/".format(, query)
    # raw = get(search_api_url)
    # if raw.status_code != 200:
    #     return CoprSearchError("Failed to get response from copr, raw response: {}".format(raw))
    #
    # result = raw.json()
    # if result["output"] != "ok":
    #     return CoprSearchError("Got bad response from copr: {}", result)
    #
    # return result.get("repos", [])


def check_copr_existence(copr_username, copr_projectname) -> bool:
    try:
        client = CoprClient(copr_url=app.config.get("COPR_BASE_URL"))
        client.get_project_details(projectname=copr_projectname, username=copr_username)
        return True
    except CoprRequestException:
        return False
