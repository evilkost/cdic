# coding: utf-8
import datetime
from pprint import pprint
import pytest

from cdic_project.cdic.logic.project_logic import ProjectLogic


def test_get_project_by_id_safe(app, f_projects):
    for p in f_projects:
        assert ProjectLogic.get_project_by_id_safe(p.id).title == p.title

    p_id = max([p.id for p in f_projects]) + 123
    assert ProjectLogic.get_project_by_id_safe(p_id) is None

    p_1 = f_projects[0]
    p_1.delete_requested_on = datetime.datetime.utcnow()
    app.session.add(p_1)
    app.session.commit()

    assert ProjectLogic.get_project_by_id_safe(p_1.id) is None
    assert ProjectLogic.get_project_by_id_safe(
        p_1.id, hide_removed=False).title == p_1.title


def test_get_projects_to_create_gh_repo(app, f_projects):

    res = ProjectLogic.get_projects_to_create_gh_repo()
    pprint(res)


def test_get_projects_to_delete(app, f_projects):

    res = ProjectLogic.get_projects_to_delete()
    pprint(res)
