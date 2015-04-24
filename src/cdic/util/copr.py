# coding: utf-8

import json
from requests import get

from ..exceptions import CoprSearchError


def search_coprs(config, query):
    search_api_url = "{}/api/coprs/search/{}/".format(config["COPR_BASE_URL"], query)
    raw = get(search_api_url)
    if raw.status_code != 200:
        return CoprSearchError("Failed to get response from copr, raw response: {}".format(raw))

    result = json.loads(raw.content)
    if result["output"] != "ok":
        return CoprSearchError("Got bad response from copr: {}", result)

    return result.get("repos", [])


