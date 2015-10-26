# coding: utf-8
import datetime
import logging

from requests import post

from .. import db
from ..models import Project

from ..logic.event_logic import create_project_event

log = logging.getLogger(__name__)


class DhLogic(object):

    @classmethod
    def trigger_build(cls, p: Project):
        url = p.dh_build_trigger_url
        log.info("Going to trigger build for: {}".format(p.repo_name))
        post(url)
        p.build_triggered_on = datetime.datetime.utcnow()
        pe = create_project_event(p, "Build request was sent to the Dockerhub")
        db.session.add_all([p, pe])

        # todo: send action

    @classmethod
    def set_dh_created(cls, p: Project):
        p.dockerhub_repo_exists = True
        pe = create_project_event(p, "Created dockerhub automated build")
        db.session.add_all([p, pe])

    @classmethod
    def set_dh_deleted(cls, p: Project):
        p.dockerhub_repo_exists = False
        pe = create_project_event(p, "Deleted dockerhub automated build")
        db.session.add_all([p, pe])

    @classmethod
    def set_build_trigger(cls, p: Project, trigger: str):
        p.dh_build_trigger_url = trigger
        pe = create_project_event(p, "Obtained dh build trigger")
        db.session.add_all([p, pe])


# def create_dockerhub_repo(project_id: int):
#     project = get_project_by_id(project_id)
#
#     if not app.dh_connector.create_project(project.repo_name):
#         return
#
#     project.dockerhub_repo_exists = True
#     pe = create_project_event(project, "Created dockerhub automated build")
#
#     db.session.add_all([project, pe])
#     db.session.commit()
#     schedule_task(start_dockerhub_build_task, project.id)
#
#
# def start_dockerhub_build(project_id: int):
#     project = get_project_by_id(project_id)
#     if project.should_start_dh_build:
#         try:
#             run_dockerhub_build(project.repo_name)
#             ev = create_project_event(project, "Build request passed to Dockerhub, wait for result")
#             project.dh_start_done_on = datetime.datetime.utcnow()
#             db.session.add_all([ev, project])
#             db.session.commit()
#             schedule_task(update_dockerhub_build_status_task, project_id)
#
#         except DockerHubQueryError:
#             log.exception("failed to start dockerhub build for: {}"
#                           .format(project.repo_name))
#
# start_dockerhub_build_task = OnDemandTask(
#     "start dockerhub automated build",
#     "{}_start_dh_build".format(PREFIX),
#     fn=ctx_wrapper(start_dockerhub_build)
# )

#
# create_dockerhub_task = OnDemandTask(
#     "create dockerhub automated build",
#     "{}_create_dockerhub".format(PREFIX),
#     fn=ctx_wrapper(create_dockerhub_repo)
# )
#

# def update_dockerhub_build_status(project_id: int):
#     project = get_project_by_id(project_id)
#     builds = get_builds_history(project.repo_name)
#     if builds:
#         log.debug("Builds for project {}: {}".format(project.repo_name, builds))
#         latest_build = builds[0]
#         new_status = latest_build["status"]
#
#         # check if we got any new info
#         if project.dockerhub_latest_build_updated_on and \
#                 project.dockerhub_latest_build_updated_on >= latest_build["updated_on"]:
#             log.debug("No new build info for project: {}".format(project.repo_name))
#             return
#
#         if project.dockerhub_build_status != "Finished" and new_status in ["Finished", "Error"]:
#             event = create_project_event(
#                 project,
#                 "Dockehub build finished with status: {}".format(new_status),
#                 event_type="dockerhub_build_finished")
#             db.session.add(event)
#
#         project.dockerhub_build_status = new_status
#         project.dockerhub_latest_build_started_on = latest_build["created_on"]
#         project.dockerhub_latest_build_updated_on = latest_build["updated_on"]
#         project.dockerhub_build_status_updated_on_local_time = datetime.datetime.utcnow()
#         db.session.add(project)
#         db.session.commit()
#     else:
#         log.debug("No builds for project: {}".format(project.repo_name))
#
# update_dockerhub_build_status_task = OnDemandTask(
#     "update dockerhub build status",
#     "{}_update_dockerhub_build_status".format(PREFIX),
#     fn=ctx_wrapper(update_dockerhub_build_status)
# )

#
# # ToDo: generalize this functions, their structure is too similiar
# def schedule_dh_status_updates(*args, **kwargs):
#     to_do = get_projects_to_update_dh_status()
#     if not to_do:
#         log.debug("No project to update dockerhub build status")
#     for project in to_do:
#         log.debug("Scheduled dockerhub build status update for: {}"
#                   .format(project.repo_name))
#         schedule_task(update_dockerhub_build_status_task, project.id)
#
#
# def reschedule_dockerhub_creation(*args, **kwargs):
#     to_do = get_projects_to_create_dh()
#     if not to_do:
#         log.debug("No project to re schedule dockerhub creation")
#     for project in to_do:
#         log.debug("Re-scheduled dockerhub creation for: {}"
#                   .format(project.repo_name))
#         schedule_task(create_dockerhub_task, project.id)
#
#
# def reschedule_dockerhub_start_build(*args, **kwargs):
#     to_do = get_projects_to_start_dh_build()
#     if not to_do:
#         log.debug("No project to re send dockerhub build request")
#     for project in to_do:
#         log.debug("Re-scheduled dockerhub start build: {}"
#                   .format(project.repo_name))
#         schedule_task(start_dockerhub_build_task, project.id)
