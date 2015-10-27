#!/usr/bin/python3
# coding: utf-8

import os
import logging

import flask
from flask_script import Manager, Command, Option


from cdic_project.util import setup_logging
from cdic_project.cdic import app, db
from cdic_project.cdic.async.runner import RunnerAlt
from cdic_project.cdic.action import run_build_async_task, delete_projects_task, create_project_repos_task

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


        import sys
        log.info("SYSPATH: {}".format(sys.path))

        # logging.getLogger("cdic_project.cdic.util.dockerhub").setLevel(logging.INFO)
        logging.getLogger("cdic_project.cdic.async.runner").setLevel(logging.INFO)
        # logging.getLogger("cdic_project.cdic.logic.build_logic").setLevel(logging.INFO)

        r = RunnerAlt(app)

        # r.register_task(create_gh_repo_task)
        # r.register_task(create_dh_repo_task)
        # r.register_task(fetch_build_trigger_task)
        r.register_task(create_project_repos_task)
        r.register_task(run_build_async_task)
        r.register_task(delete_projects_task)

        r.start()


manager.add_command("create_sqlite_file", CreateSqliteFileCommand())
manager.add_command("create_db", CreateDBCommand())
manager.add_command("drop_db", DropDBCommand())

manager.add_command("run_async_tasks", RunAsyncTasks())

if __name__ == '__main__':
    manager.run()
