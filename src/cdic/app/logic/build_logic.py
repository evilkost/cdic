# coding: utf-8

import datetime
import json
import logging
import time

from .. import db, app
from ..models import Project
from ..constants import EventType
from ..logic.event_logic import create_project_event
from ..logic.github_logic import set_github_repo_created
from ..logic.dockerhub_logic import create_dockerhub_task
from ..logic.project_logic import update_patched_dockerfile, get_project_by_id, get_running_projects
from ..util.github import GhClient
from ..builder import push_build
from ..async.task import OnDemandTask
from ..async.pusher import schedule_task, PREFIX, ctx_wrapper

log = logging.getLogger(__name__)


def run_build(project_id):
    project = get_project_by_id(project_id)

    update_patched_dockerfile(project)
    build_event = create_project_event(
        project, "Started new build",
        data_json=json.dumps({"build_requested_dt": datetime.datetime.utcnow().isoformat()}),
        event_type=EventType.BUILD_REQUESTED
    )
    db.session.add_all([project, build_event])
    db.session.commit()
    if not project.github_repo_exists:
        create_single_github_repo(project)

    push_build(project)

    if project.dockerhub_repo_exists:
        pe = create_project_event(project, "Build request passed to Dockerhub, wait for result")
        db.session.add(pe)
    else:
        schedule_task(create_dockerhub_task, project.id)
        pe = create_project_event(project, "Dockerhub automated build repo is scheduled for creation, "
                                           "please wait")
        db.session.add(pe)

    project.build_is_running = False
    db.session.add(project)
    db.session.commit()


def create_single_github_repo(prj: Project, *args, **kwargs):
    repo_name = prj.repo_name
    log.info("Creating repo: {}".format(repo_name))
    client = GhClient(app.config)
    client.create_repo(repo_name)
    set_github_repo_created(prj)


def schedule_build(project):
    project.build_is_running = True
    project.build_started_on = datetime.datetime.utcnow()
    db.session.add(project)
    db.session.commit()
    schedule_task(run_build_task, project.id)

run_build_task = OnDemandTask(
    "run build",
    "{}_run_build".format(PREFIX),
    fn=ctx_wrapper(run_build)
)


def reschedule_stall_builds(*args, **kwargs):
    """
    Find project that  has (local_repo_pushed_on < build_started_on)
        && (now - build_start_on) > 120 seconds
    and send build task again
    """
    project_list = get_running_projects().all()
    if not project_list:
        log.debug("No builds to reschedule")
        return

    log.info("Rescheduling stale build")
    for project in project_list:
        if project.local_repo_pushed_on is None or \
                project.local_repo_pushed_on < project.build_started_on or \
                (datetime.datetime.utcnow() - project.build_started_on).seconds > 120:

            log.info("re scheduled build task: {}".format(project.repo_name))
            schedule_task(run_build_task, project.id)
