#!/usr/bin/python3
# coding: utf-8
from functools import partial

import os
import logging

import flask
from flask_script import Manager, Command, Option, Group

from app import app, db
from app.builder import run_builds
from app.internal_api import Api

from app.util.dockerhub import create_pending_dockerhub
from app.util.github import create_github_repo
from async_runner import Runner

from cdic.util import setup_logging

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
        setup_logging("/tmp/cdic_async_tasks.log")

        api = Api()
        r = Runner(app)

        def wrapped(fn, *args, **kwargs):
            with app.app_context():
                fn(*args, **kwargs)

        r.add_periodic_task("Create github repos", partial(wrapped, create_github_repo, api), 5)
        r.add_periodic_task("Run builds", partial(wrapped, run_builds), 10)
        r.add_periodic_task("Create pending dockerhub", partial(wrapped, create_pending_dockerhub, api), 20)

        r.start()
        # create_github_repo(api)
        #run_builds()
        #create_pending_dockerhub(api)


manager.add_command("create_sqlite_file", CreateSqliteFileCommand())
manager.add_command("create_db", CreateDBCommand())
manager.add_command("drop_db", DropDBCommand())

manager.add_command("run_async_tasks", RunAsyncTasks())

if __name__ == '__main__':
    manager.run()
