# coding: utf-8

from flask import abort
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.query import Query

from ..models import Project, User, LinkedCopr


def check_link_exists(project: Project, username: str, coprname: str) -> bool:
    query = (
        LinkedCopr.query
        .filter(LinkedCopr.project_id == project.id)
        .filter(LinkedCopr.username == username)
        .filter(LinkedCopr.coprname == coprname)
    )
    if len(query.all()) > 0:
        return True
    else:
        return False


def create_link(project: Project, username: str, coprname: str,) -> LinkedCopr:
    if check_link_exists(project, username, coprname):
        return
    else:
        return LinkedCopr(
            project=project,
            username=username,
            coprname=coprname,
        )


def get_link_by_id(link_id: int) -> LinkedCopr:
    return LinkedCopr.query.get(link_id)


# def unlink_copr(link_id: int):
#     link = get_link_by_id(link_id)
#     if link:
#         db.session.
