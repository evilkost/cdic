# coding: utf-8

from backports.typing import Iterable, List

from .models import Project


def project_list_to_ids(projects: Iterable[Project]) -> List[int]:
    return [p.id for p in projects]
