# coding: utf-8

from flask import abort
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.query import Query

from ..models import Project, User
from ..forms.project import ProjectForm


def get_all_projects_query() -> Query:
    return Project.query.order_by(Project.created_on.desc())


def get_projects_by_user(user: User) -> Query:
    """
    :param User user: user instance
    :return query to List[Project]: projects owned by `user`
    """
    return Project.query.filter(User.id == user.id)


def get_project_by_title(user: User, title: str) -> Project:
    """
    :raises NoResultFound: when no such project exists
    """
    return Project.query.filter(User.id == user.id).filter_by(title=title).one()


def get_project_by_id(ident: int) -> Project:
    """
    :raises NoResultFound: when no such project exists
    """
    return Project.query.get(ident)


def exists_for_user(user: User, title: str) -> bool:
    try:
        get_project_by_title(user, title)
        return True
    except NoResultFound:
        return False


def add_project_from_form(user: User, form: ProjectForm) -> Project:
    if exists_for_user(user, form.title.data):
        abort(400)
    else:
        return Project(
            user=user,
            title=form.title.data,
            source_mode=form.source_mode.data,
        )


def update_project_from_form(project: Project, form: ProjectForm) -> Project:
    project.source_mode = form.source_mode.data
    project.local_text = form.local_text.data
    project.git_url = form.git_url.data
