# coding: utf-8
import pytest

from cdic_project.cdic.models import User, Project


def test_user(app):
    name = "foo"

    u = User(
        username=name,
        mail="foo@example.com"
    )

    app.session.add(u)
    app.session.commit()

    u1 = User.query.filter(User.username == name).one()

    assert u1.id == u.id
    assert u1.name == name


def test_project(app, f_users):
    u1 = f_users[0]
    title = "test_1"
    p = Project(user=u1,
                title=title)

    app.session.add(p)
    app.session.commit()

    p_list = Project.query.filter(User.id == u1.id).all()
    assert len(p_list) == 1
    assert p_list[0].title == title




