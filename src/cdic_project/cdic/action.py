# coding: utf-8


import datetime
import logging

from typing import List, Iterable
from . import db, dh_connector, git_store
from .util.github import GhClient
from .models import Project
from .logic.github_logic import GhLogic

from .logic.dockerhub_logic import DhLogic
from .logic.project_logic import ProjectLogic
from .async.task import TaskDef
from .async.pusher import ctx_wrapper, schedule_task_async

log = logging.getLogger(__name__)


def run_build(project_id):
    p = ProjectLogic.get_project_by_id_safe(project_id)
    if not p:
        return

    # here we expect that we already have GH and DH repos and url to trigger builds
    # so we need to do the following steps
    # 0. create local repo if it doesn't exist
    # 1. commit changes (if any) and push them to GH
    # 2. trigger new DH build
    # 3. issue task to fetch build status

    # not sure if we need this, since edit should also invoke update_dockerfile
    ProjectLogic.update_dockerfile(p, silent=True)
    db.session.commit()

    if p.dh_build_trigger_url is None:
        log.info("DH build trigger url not defined yet; build request is postponed")

    if not p.local_repo_exists:
        ProjectLogic.init_local_repo(p)
        db.session.commit()

    if ProjectLogic.should_commit_changes(p):
        GhLogic.update_local_repo(p)
        db.session.commit()

    if ProjectLogic.should_push_changes(p):
        GhLogic.push_changes(p)
        db.session.commit()

    if ProjectLogic.should_send_build_trigger(p):
        DhLogic.trigger_build(p)
        db.session.commit()

        # todo: send task to query build status


def pack_p_ids(projects: Iterable[Project]):
    return [([p.id], {}) for p in projects]


def run_build_do_reschedule():
    return pack_p_ids(ProjectLogic.get_projects_to_run_build_again())


run_build_async_task = TaskDef(
    channel="run_build",
    work_fn=ctx_wrapper(run_build),
    reschedule_fn=ctx_wrapper(run_build_do_reschedule)
)


def run_build_async(project: Project):
    # todo: should we do some checks here?
    #
    project.build_requested_on = datetime.datetime.utcnow()
    db.session.add(project)
    db.session.commit()

    schedule_task_async(run_build_async_task, project.id)

# TODO: implement
query_builds_status = TaskDef(
    channel="query_builds",
    work_fn=None,
    reschedule_fn=None
)


def create_project_repos(project_id: int):
    p = ProjectLogic.get_project_by_id_safe(project_id)
    if not p:
        return
    repo_name = p.repo_name
    if not p.github_repo_exists:
        log.info("Creating github repo: {}".format(repo_name))
        client = GhClient()
        client.create_repo(repo_name)
        # todo: check if gh repo was created
        GhLogic.set_github_repo_created(p)
        db.session.commit()
    else:
        log.info("Github repo {} already exists".format(repo_name))

    if not p.dockerhub_repo_exists:
        log.info("Creating dockerhub repo: {}".format(repo_name))
        if dh_connector.create_project(repo_name):
            DhLogic.set_dh_created(p)
            db.session.commit()
            log.info("Dockerhub repo created: {}".format(repo_name))
        else:
            return
    else:
        log.info("Dockerhub repo {} already exists".format(repo_name))

    if p.dh_build_trigger_url is None:
        log.info("Fetching dockerhub build trigger url: {}".format(repo_name))
        mb_trigger = dh_connector.get_build_trigger_url(repo_name)
        if mb_trigger:
            DhLogic.set_build_trigger(p, mb_trigger)
            db.session.commit()
            log.info("Obtained dh build trigger for: {}"
                     .format(repo_name))
    else:
        log.info("Build trigger for repo {} is already fetched".format(repo_name))

    if p.build_requested_on is not None:
        schedule_task_async(run_build_async_task, project_id)

create_project_repos_task = TaskDef(
    channel="create_project_repos",
    work_fn=ctx_wrapper(create_project_repos),
    reschedule_fn=ctx_wrapper(
        lambda: pack_p_ids(
            ProjectLogic.get_projects_repo_creation_not_done())
    )
)


def delete_project(project_id: int):
    p = ProjectLogic.get_project_by_id_safe(project_id, hide_removed=False)
    if p is None:
        return
    if p.delete_requested_on is None:
        return

    log.info("Going to delete project: {}".format(p.repo_name))
    if p.dockerhub_repo_exists:
        if dh_connector.delete_project(p.repo_name):
            DhLogic.set_dh_deleted(p)
            db.session.commit()
        else:
            return

    if p.github_repo_exists:
        client = GhClient()
        if client.delete_repo(p.repo_name):
            GhLogic.set_github_repo_deleted(p)
            db.session.commit()
        else:
            return

    if p.local_repo_exists:
        git_store.remove_local(p.user.username, p.title)
        p.local_repo_exists = False
        db.session.commit()

    ProjectLogic.delete_project_with_events(p)
    db.session.commit()

    log.info("Project id #{} is removed".format(project_id))


delete_projects_task = TaskDef(
    channel="delete_project",
    work_fn=ctx_wrapper(delete_project),
    reschedule_fn=ctx_wrapper(
        lambda: pack_p_ids(ProjectLogic.get_projects_to_delete())
    )
)


def update_builds_info(project_id: int):
    p = ProjectLogic.get_project_by_id_safe(project_id)
    if p is None:
        return

    log.info("Going to update build statuses for: {}".format(p.repo_name))
    # if ProjectLogic.should_fetch_builds_statuses_for_project(p):
    if True:
        statuses = dh_connector.fetch_builds_status(p.repo_name)

        for bs in statuses:
            build = ProjectLogic.get_or_create_build_info_from_bs(p, bs)
            ProjectLogic.update_build_info_status(build, bs)

        db.session.add(p)
        db.session.commit()

    for build in ProjectLogic.get_builds_to_update_details(p):
        log.info("Going to update details for repo: {}, build: {}"
                 .format(p.repo_name, build.id))
        details = dh_connector.get_build_details(p.repo_name, build.id)
        if details:
            log.info("Got details")
            ProjectLogic.update_build_info_details(build, details)
        else:
            log.info("Failed to get details")

    if db.session.dirty:
        db.session.commit()


fetch_builds_status_task = TaskDef(
    channel="fetch_builds_status",
    work_fn=ctx_wrapper(update_builds_info),
    reschedule_fn=ctx_wrapper(
        lambda: pack_p_ids(ProjectLogic.get_projects_to_update_builds())
    )
)
