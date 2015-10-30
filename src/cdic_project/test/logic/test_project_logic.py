# coding: utf-8
import datetime
from pprint import pprint

import arrow
import pytest

from cdic_project.cdic.models import DhBuildInfo, Project
from cdic_project.cdic.util.dockerhub import BuildStatus, BuildDetails
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


# def test_get_projects_to_delete(app, f_projects):
#
#     res = ProjectLogic.get_projects_to_delete()
#     pprint(res)


def test_get_or_create_build_info(app, f_projects):
    p = f_projects[0]
    bs = BuildStatus(
        repo_name="foobar",
        build_id="12345",
        href="http://example.com/afasdfgt",
        status="pending"
    )

    ProjectLogic.get_or_create_build_info_from_bs(p, bs)
    app.db.session.commit()

    # import ipdb; ipdb.set_trace()
    bi_list = DhBuildInfo.query.all()
    assert len(bi_list) == 1
    bi = bi_list[0]
    assert bi.id == bs.build_id
    assert bi.status == bs.status

    ProjectLogic.get_or_create_build_info_from_bs(p, bs)
    app.db.session.commit()
    bi_list = DhBuildInfo.query.all()
    assert len(bi_list) == 1

    bs_2 = BuildStatus(
        repo_name="foobar2",
        build_id="9123asd45",
        href="http://example.com/afasdfqat31gt",
        status="pending"
    )

    ProjectLogic.get_or_create_build_info_from_bs(p, bs_2)
    app.db.session.commit()
    bi_list = DhBuildInfo.query.all()
    assert len(bi_list) == 2
    assert set([x.id for x in bi_list]) == {bs.build_id, bs_2.build_id}


def test_update_build_status(app, f_projects):
    p = f_projects[0]
    bs = BuildStatus(
        repo_name="foobar",
        build_id="12345",
        href="http://example.com/afasdfgt",
        status="pending"
    )

    ProjectLogic.get_or_create_build_info_from_bs(p, bs)
    app.db.session.commit()

    build = ProjectLogic.get_or_create_build_info_from_bs(p, bs)
    status_updated_on_first = build.status_updated_on

    ProjectLogic.update_build_info_status(build, bs)
    app.db.session.commit()

    bi_list = DhBuildInfo.query.all()
    assert len(bi_list) == 1
    bi = bi_list[0]
    assert bi.id == bs.build_id
    assert bi.status == bs.status
    assert bi.status_updated_on == status_updated_on_first

    bs.status = "failed"
    ProjectLogic.update_build_info_status(build, bs)
    app.db.session.commit()

    bi_list = DhBuildInfo.query.all()
    assert len(bi_list) == 1
    bi = bi_list[0]
    assert bi.id == bs.build_id
    assert bi.status == bs.status
    assert bi.status_updated_on > status_updated_on_first

    # prj = ProjectLogic.get_project_by_id(p.id)


def test_update_build_details(app, f_projects):
    p = f_projects[0]
    bs = BuildStatus(
        repo_name="foobar",
        build_id="12345",
        href="http://example.com/afasdfgt",
        status="pending"
    )

    ProjectLogic.get_or_create_build_info_from_bs(p, bs)
    app.db.session.commit()

    build = ProjectLogic.get_or_create_build_info_from_bs(p, bs)

    details = BuildDetails(
        info_table={
            "foo": "bar"
        },
        logs="Lorem ipsum dolor sit amet"
    )

    ProjectLogic.update_build_info_details(build, details)
    app.db.session.commit()

    build2 = ProjectLogic.get_or_create_build_info_from_bs(p, bs)

    assert build2.details["info_table"] == details.info_table
    assert build2.details["logs"] == details.logs


# def test_store_build_info_info(app, f_projects):
#     p = f_projects[0]
#     bs = BuildStatus(
#         repo_name="foobar",
#         build_id="12345",
#         href="http://example.com/afasdfgt",
#         status="pending"
#     )
#
#     old_bi = ProjectLogic.store_build_info(p, bs)
#     app.db.session.commit()
#
#     details = BuildDetails(
#         info_table={"foo": "bar"},
#         logs="Lorem ipsum dolor sit amet"
#     )
#
#     new_bi = ProjectLogic.store_build_info(p, old_bi=old_bi, details=details)
#     app.db.session.commit()
#     # import ipdb; ipdb.set_trace()
#     bi_list = DhBuildInfo.query.all()
#
#     assert len(bi_list) == 1
#     bi = bi_list[0]
#     assert bi.details["info_table"] == details.info_table


def get_fresh_p(p: Project) -> Project:
    return ProjectLogic.get_project_by_id(p.id)


def test_should_get_builds_statuses(app, f_projects):
    p = f_projects[0]
    assert ProjectLogic.should_fetch_builds_statuses_for_project(get_fresh_p(p)) is False
    wp = get_fresh_p(p)
    wp.build_triggered_on = arrow.utcnow()
    app.db.session.add(wp)
    app.db.session.commit()
    assert ProjectLogic.should_fetch_builds_statuses_for_project(get_fresh_p(p)) is True

    bs = BuildStatus(
        repo_name="foobar",
        build_id="12345",
        href="http://example.com/afasdfgt",
        status="pending"
    )
    #
    ProjectLogic.get_or_create_build_info_from_bs(p, bs)
    app.db.session.commit()
    assert ProjectLogic.should_fetch_builds_statuses_for_project(get_fresh_p(p)) is False

    wp = get_fresh_p(p)
    wp.build_triggered_on = arrow.utcnow()
    app.db.session.add(wp)
    app.db.session.commit()

    assert ProjectLogic.should_fetch_builds_statuses_for_project(get_fresh_p(p)) is True
