# coding: utf-8


import datetime
from functools import partial
import json
import logging
import time

from . import db, app
from backports.typing import Callable, List
from .util.github import GhClient
from .models import Project
from .logic.github_logic import GhLogic
from .logic.dockerhub_logic import create_dockerhub_task, start_dockerhub_build_task, DhLogic
from .logic.project_logic import update_patched_dockerfile, get_project_by_id, get_running_projects, ProjectLogic
from .async.task import OnDemandTask, TaskDef
from .async.pusher import schedule_task, PREFIX, ctx_wrapper, schedule_task_async

log = logging.getLogger(__name__)


def run_build(project_id):
    project = get_project_by_id(project_id)
    if project.delete_requested_on is not None:
        return

    # here we expect that we already have GH and DH repos and url to trigger builds
    # so we need to do the following steps
    # 1. commit changes (if any) and push them to GH
    # 2. trigger new DH build
    # 3. issue task to fetch build status

    # not sure if we need this, since edit should also do update_dockerfile
    ProjectLogic.update_dockerfile(project, silent=True)
    db.session.commit()

    if ProjectLogic.should_commit_changes(project):
        GhLogic.update_local_repo(project)
        db.session.commit()

    if ProjectLogic.should_push_changes(project):
        GhLogic.push_changes(project)
        db.session.commit()

    if ProjectLogic.should_send_build_trigger(project):
        DhLogic.trigger_build(project)
        db.session.commit()

        # todo: send task to query build status

# def reschedule_projects_from_func(
#         task_def: TaskDef,
#         func: Callable[(),List[Project]]):
#     for p in func():
#         schedule_task_async(task_def, p.id)


def pack_p_ids(projects: List[Project]):
    return [([p.id], {}) for p in projects]


def run_build_do_reschedule():
    return pack_p_ids(ProjectLogic.get_projects_to_run_build_again())


run_build_async_task = TaskDef(
    channel="run_build",
    work_fn=ctx_wrapper(run_build),
    # on_success=trigger_new_build,
    # on_error=partial(halt_build, "Failed to push changes to github"),
    reschedule_fn=ctx_wrapper(run_build_do_reschedule)
)


def run_build_async(project: Project):
    # todo: should we do some checks here?
    #
    project.build_requested_on = datetime.datetime.utcnow()
    db.session.add(project)
    db.session.commit()

    schedule_task_async(run_build_async_task, project.id)


query_builds_status = TaskDef(
    channel="query_builds",
    work_fn=None,
    reschedule_fn=None
)


def create_gh_repo(project_id: int):
    p = get_project_by_id(project_id)
    if p.delete_requested_on is not None:
        return
    repo_name = p.repo_name
    if not p.github_repo_exists:
        log.info("Creating github repo: {}".format(repo_name))
        client = GhClient()
        client.create_repo(repo_name)
        GhLogic.set_github_repo_created(p)
        db.session.commit()
    else:
        log.info("Github repo {} already exists".format(repo_name))

    schedule_task_async(create_dh_repo_task, project_id)


create_gh_repo_task = TaskDef(
    channel="create_gh_repo",
    work_fn=ctx_wrapper(create_gh_repo),
    reschedule_fn=ctx_wrapper(
        lambda: pack_p_ids(ProjectLogic.get_projects_to_create_gh_repo())
    )
)


def create_dh_repo(project_id: int):
    p = get_project_by_id(project_id)
    if p.delete_requested_on is not None:
        return
    repo_name = p.repo_name
    if not p.dockerhub_repo_exists:
        log.info("Creating dockerhub repo: {}".format(repo_name))
        if app.dh_connector.create_project(repo_name):
            DhLogic.set_dh_created(p)
            db.session.commit()
            log.info("Dockerhub repo created: {}".format(repo_name))
            schedule_task_async(fetch_build_trigger_task, project_id)
    else:
        schedule_task_async(fetch_build_trigger_task, project_id)
        log.info("Dockerhub repo {} already exists".format(repo_name))


create_dh_repo_task = TaskDef(
    channel="create_dh_repo",
    work_fn=ctx_wrapper(create_dh_repo),
    reschedule_fn=ctx_wrapper(
        lambda: pack_p_ids(ProjectLogic.get_projects_to_create_dh_repo())
    ),
)


def get_dh_trigger_url(project_id: int):
    p = get_project_by_id(project_id)
    if p.delete_requested_on is not None:
        return
    repo_name = p.repo_name
    if p.dh_build_trigger_url is None:
        log.info("Fetching dockerhub build trigger url: {}".format(repo_name))
        mb_trigger = app.dh_connector.get_build_trigger_url(repo_name)
        if mb_trigger:
            DhLogic.set_build_trigger(p, mb_trigger)
            db.session.commit()
            log.info("Obtained dh build trigger for: {}"
                     .format(repo_name))

    else:
        log.info("Build trigger for repo {} is already fetched".format(repo_name))

fetch_build_trigger_task = TaskDef(
    channel="fetch_build_trigger",
    work_fn=ctx_wrapper(get_dh_trigger_url),
    reschedule_fn=ctx_wrapper(
        lambda: pack_p_ids(ProjectLogic.get_projects_to_fetch_build_trigger())
    )
)
