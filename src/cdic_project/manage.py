#!/usr/bin/python3
# coding: utf-8
from functools import partial

import os
import logging

import flask
from flask_script import Manager, Command, Option, Group


from cdic_project.cdic.logic.project_logic import process_pending_deletes

from cdic_project.util import setup_logging

# from cdic_project.cdic.logic.build_logic import run_build_task
from cdic_project.cdic.logic.dockerhub_logic import create_dockerhub_task, update_dockerhub_build_status_task, \
    schedule_dh_status_updates, reschedule_dockerhub_creation, reschedule_dockerhub_start_build, \
    start_dockerhub_build_task
from cdic_project.cdic import app, db
# from cdic_project.cdic.logic.build_logic import reschedule_stall_builds
from cdic_project.cdic.async.runner import Runner, RunnerAlt
from cdic_project.cdic.async.pusher import ctx_wrapper
from cdic_project.cdic.action import create_gh_repo_task, create_dh_repo_task, fetch_build_trigger_task, \
    run_build_async_task

manager = Manager(app)

log = logging.getLogger(__name__)


class CreateSqliteFileCommand(Command):

    """
    Create the sqlite DB file (not the tables).
    Used for alembic, "create_db" does this automatically.
    """

    def run(self):
        if flask.current_app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
            # strip sqlite:///
            datadir_name = os.path.dirname(
                flask.current_app.config["SQLALCHEMY_DATABASE_URI"][10:])
            if not os.path.exists(datadir_name):
                os.makedirs(datadir_name)


class CreateDBCommand(Command):

    """
    Create the DB schema
    """

    def run(self, alembic_ini=None):
        CreateSqliteFileCommand().run()
        db.create_all()

        # load the Alembic configuration and generate the
        # version table, "stamping" it with the most recent rev:
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(alembic_ini)
        command.stamp(alembic_cfg, "head")  # (*)

    option_list = (
        Option("--alembic",
               "-f",
               dest="alembic_ini",
               help="Path to the alembic configuration file (alembic.ini)",
               required=True),
    )


class DropDBCommand(Command):

    """
    Delete DB
    """

    def run(self):
        db.drop_all()


class RunAsyncTasks(Command):
    """
    Run cdic tasks like docker hub repo creation
    """
    def run(self):
        setup_logging(app.config["ASYNC_LOG"])

        # logging.getLogger("cdic_project.cdic.util.dockerhub").setLevel(logging.INFO)
        logging.getLogger("cdic_project.cdic.async.runner").setLevel(logging.INFO)
        # logging.getLogger("cdic_project.cdic.logic.build_logic").setLevel(logging.INFO)

        r = RunnerAlt(app)

        r.register_task(create_gh_repo_task)
        r.register_task(create_dh_repo_task)
        r.register_task(fetch_build_trigger_task)
        r.register_task(run_build_async_task)

        # r = Runner(app)
        #
        # r.add_periodic_task("Reschedule build task", ctx_wrapper(reschedule_stall_builds), 200)
        # r.add_periodic_task("Schedule dh status update task",
        #                     ctx_wrapper(schedule_dh_status_updates), 200)
        # r.add_periodic_task("Reschedule failed dockerhub creation task",
        #                     ctx_wrapper(reschedule_dockerhub_creation), 120)
        # r.add_periodic_task("Reschedule dockerhub start build task",
        #                     ctx_wrapper(reschedule_dockerhub_start_build), 40)
        # r.add_periodic_task("Periodically process delete project requests",
        #                     ctx_wrapper(process_pending_deletes), 40)
        #
        # all_async_tasks = [
        #     run_build_task,
        #     create_dockerhub_task,
        #     update_dockerhub_build_status_task,
        #     start_dockerhub_build_task,
        # ]
        #
        # for task in all_async_tasks:
        #     r.add_on_demand_task(task)

        r.start()


manager.add_command("create_sqlite_file", CreateSqliteFileCommand())
manager.add_command("create_db", CreateDBCommand())
manager.add_command("drop_db", DropDBCommand())

manager.add_command("run_async_tasks", RunAsyncTasks())

if __name__ == '__main__':
    manager.run()
