# # coding: utf-8
#
# import datetime
# from functools import partial
# import json
# import logging
# import time
#
# from .. import db, app
# from ..helpers import project_list_to_ids
# from ..models import Project
# from ..constants import EventType
# from ..logic.event_logic import create_project_event
# from ..logic.github_logic import set_github_repo_created, GhLogic
# from ..logic.dockerhub_logic import create_dockerhub_task, start_dockerhub_build_task, DhLogic
# from ..logic.project_logic import update_patched_dockerfile, get_project_by_id, get_running_projects, ProjectLogic
# from ..util.github import GhClient
# from ..builder import push_build
# from ..async.task import OnDemandTask, TaskDef
# from ..async.pusher import schedule_task, PREFIX, ctx_wrapper, schedule_task_async
#
# log = logging.getLogger(__name__)
#
#
# def run_build(project_id):
#     project = get_project_by_id(project_id)
#     if project.delete_requested_on is not None:
#         return
#
#     # here we expect that we already have GH and DH repos and url to trigger builds
#     # so we need to do the following steps
#     # 1. commit changes (if any) and push them to GH
#     # 2. trigger new DH build
#     # 3. issue task to fetch build status
#
#     # not sure if we need this, since edit should also do update_dockerfile
#     ProjectLogic.update_dockerfile(project, silent=True)
#     db.session.commit()
#
#     if ProjectLogic.should_commit_changes(project):
#         GhLogic.update_local_repo(project)
#         db.session.commit()
#
#     if ProjectLogic.should_push_changes(project):
#         GhLogic.push_changes(project)
#         db.session.commit()
#
#     if ProjectLogic.should_send_build_trigger(project):
#         DhLogic.trigger_build(project)
#         db.session.commit()
#
#         # todo: send task to query build status
#
#
# def run_build_do_reschedule():
#     projects = ProjectLogic.get_projects_to_run_build_again()
#     for p in projects:
#         schedule_task_async(run_build_async_task, p.id)
#
#
# run_build_async_task = TaskDef(
#     channel="run_build",
#     work_fn=ctx_wrapper(run_build),
#     # on_success=trigger_new_build,
#     # on_error=partial(halt_build, "Failed to push changes to github"),
#     reschedule_fn=ctx_wrapper(run_build_do_reschedule)
# )
#
#
# def schedule_build(project: Project):
#     # todo: should we do some checks here?
#     #
#     # project.build_started_on = datetime.datetime.utcnow()
#     project.build_requested_on = datetime.datetime.utcnow()
#     db.session.add(project)
#     db.session.commit()
#
#     schedule_task_async(run_build_async_task, project.id)
#
#
# query_builds_status = TaskDef(
#     channel="query_builds",
#     work_fn=None,
#     reschedule_fn=None
# )
#
#
# # older stuff
# #
# # def run_build_old(project_id):
# #     project = get_project_by_id(project_id)
# #     if project.delete_requested_on is not None:
# #         return
# #
# #     update_patched_dockerfile(project)
# #     build_event = create_project_event(
# #         project, "Started new build",
# #         data_json=json.dumps({"build_requested_dt": datetime.datetime.utcnow().isoformat()}),
# #         event_type=EventType.BUILD_REQUESTED
# #     )
# #     db.session.add_all([project, build_event])
# #     db.session.commit()
# #     if not project.github_repo_exists:
# #         create_single_github_repo(project)
# #
# #     push_build(project)
# #
# #     if not project.dockerhub_repo_exists:
# #         schedule_task(create_dockerhub_task, project.id)
# #         pe = create_project_event(project, "Dockerhub automated build repo is scheduled for creation, "
# #                                            "please wait")
# #         db.session.add(pe)
# #
# #     project.dh_start_requested_on = datetime.datetime.utcnow()
# #     project.build_is_running = False
# #     db.session.add(project)
# #     db.session.commit()
# #     schedule_task(start_dockerhub_build_task, project_id)
# #
# #
# # def create_single_github_repo(prj: Project, *args, **kwargs):
# #     repo_name = prj.repo_name
# #     log.info("Creating repo: {}".format(repo_name))
# #     client = GhClient()
# #     client.create_repo(repo_name)
# #     set_github_repo_created(prj)
# #
# #
# # def schedule_build(project):
# #     project.build_is_running = True
# #     project.build_started_on = datetime.datetime.utcnow()
# #     db.session.add(project)
# #     db.session.commit()
# #     schedule_task(run_build_task, project.id)
# #
# # run_build_task = OnDemandTask(
# #     "run build",
# #     "{}_run_build".format(PREFIX),
# #     fn=ctx_wrapper(run_build)
# # )
# #
# #
# # def reschedule_stall_builds(*args, **kwargs):
# #     """
# #     Find project that  has (local_repo_pushed_on < build_started_on)
# #         && (now - build_start_on) > 120 seconds
# #     and send build task again
# #     """
# #     project_list = get_running_projects()
# #     if not project_list:
# #         log.debug("No builds to reschedule")
# #         return
# #
# #     log.info("Rescheduling stale build")
# #     for project in project_list:
# #         if project.local_repo_pushed_on is None or \
# #                 project.local_repo_pushed_on < project.build_started_on or \
# #                 (datetime.datetime.utcnow() - project.build_started_on).seconds > 120:
# #
# #             log.info("re scheduled build task: {}".format(project.repo_name))
# #             schedule_task(run_build_task, project.id)
