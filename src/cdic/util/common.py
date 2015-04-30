# coding: utf-8

from urllib.parse import urlparse

def get_root_from_url(url: str) -> str:
    """
    :return: Url to the server root
    """
    parsed = urlparse(url)

    return
