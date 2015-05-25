# coding: utf-8

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.query import Query

from ..models import User


def get_user_by_name(username: str) -> User:
    """
    :param str username: name to query
    :return User: user object
    :raises NoResultFound: when no user with such name
    """
    return User.query.filter_by(username=username).one()


