# coding: utf-8

import logging

from .. import db
from ..util.dockerhub import create_dockerhub_automated_build_repo, get_builds_history
from ..models import Project
from ..logic.event_logic import create_project_event
from ..logic.project_logic import get_project_by_id, get_projects_to_update_dh_status, get_projects_to_create_dh
from ..async.task import OnDemandTask
from ..async.pusher import PREFIX, ctx_wrapper, schedule_task

log = logging.getLogger(__name__)


def set_docker_repo_created(project: Project):
    project.dockerhub_repo_exists = True

    pe = create_project_event(project, "Created dockerhub automated build")
    if project.build_is_running:
        # first ever build,
        pe2 = create_project_event(project, "Build request passed to Dockerhub, wait for result")
        db.session.add(pe2)
        project.build_is_running = False

    db.session.add_all([project, pe])


def create_dockerhub_repo(project_id: int):
    project = get_project_by_id(project_id)
    create_dockerhub_automated_build_repo(project.repo_name)
    set_docker_repo_created(project)
    db.session.commit()


create_dockerhub_task = OnDemandTask(
    "create dockerhub automated build",
    "{}_create_dockerhub".format(PREFIX),
    fn=ctx_wrapper(create_dockerhub_repo)
)


def update_dockerhub_build_status(project_id: int):
    project = get_project_by_id(project_id)
    builds = get_builds_history(project.repo_name)
    if builds:
        log.debug("Builds for project {}: {}".format(project.repo_name, builds))
        latest_build = builds[0]
        new_status = latest_build["status"]
        if project.dockerhub_build_status != "Finished" and new_status in ["Finished", "Error"]:
            event = create_project_event(
                project,
                "Dockehub build finished with status: {}".format(new_status),
                event_type="dockerhub_build_finished")
            db.session.add(event)

        project.dockerhub_build_status = new_status
        project.dockerhub_latest_build_started_on = latest_build["created_on"]
        project.dockerhub_latest_build_updated_on = latest_build["updated_on"]
        db.session.add(project)
        db.session.commit()
    else:
        log.debug("No builds for project: {}".format(project.repo_name))

update_dockerhub_build_status_task = OnDemandTask(
    "update dockerhub build status",
    "{}_update_dockerhub_build_status".format(PREFIX),
    fn=ctx_wrapper(update_dockerhub_build_status)
)


def schedule_dh_status_updates(*args, **kwargs):
    to_do = get_projects_to_update_dh_status()
    if not to_do:
        log.debug("No project to update dockerhub build status")
    for project in to_do:
        log.debug("Scheduled dockerhub build status update for : {}"
                  .format(project.repo_name))
        schedule_task(update_dockerhub_build_status_task, project.id)

def reschedule_dockerhub_creation(*args, **kwargs):
    to_do = get_projects_to_create_dh()
    if not to_do:
        log.debug("No project to re schedule dockerhub creation")
    for project in to_do:
        log.debug("Re-scheduled dockerhub creation for : {}"
                  .format(project.repo_name))
        schedule_task(create_dockerhub_task, project.id)
