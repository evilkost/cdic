#!/usr/bin/python3
# coding: utf-8
from functools import partial

import os
import logging

import flask
from flask_script import Manager, Command, Option, Group


from cdic.util import setup_logging

from app.logic.build_logic import run_build_task
from app.logic.dockerhub_logic import create_dockerhub_task, update_dockerhub_build_status_task, \
    schedule_dh_status_updates, reschedule_dockerhub_creation
from app import app, db
from app.logic.build_logic import reschedule_stall_builds
from app.async.runner import Runner
from app.async.pusher import ctx_wrapper


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

        logging.getLogger("app.util.dockerhub").setLevel(logging.INFO)
        logging.getLogger("app.async.runner").setLevel(logging.INFO)
        logging.getLogger("app.logic.build_logic").setLevel(logging.INFO)

        r = Runner(app)

        r.add_periodic_task("Reschedule build task", ctx_wrapper(reschedule_stall_builds), 200)
        r.add_periodic_task("Schedule dh status update task",
                            ctx_wrapper(schedule_dh_status_updates), 200)
        r.add_periodic_task("Reschedule failed dockerhub creation task",
                            ctx_wrapper(reschedule_dockerhub_creation), 120)

        all_async_tasks = [
            run_build_task,
            create_dockerhub_task,
            update_dockerhub_build_status_task,
        ]

        for task in all_async_tasks:
            r.add_on_demand_task(task)

        r.start()


manager.add_command("create_sqlite_file", CreateSqliteFileCommand())
manager.add_command("create_db", CreateDBCommand())
manager.add_command("drop_db", DropDBCommand())

manager.add_command("run_async_tasks", RunAsyncTasks())

if __name__ == '__main__':
    manager.run()
