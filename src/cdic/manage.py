#!/usr/bin/python3
# coding: utf-8

import os
import logging

import flask
from flask_script import Manager, Command, Option, Group

from app import app, db
from app.builder import run_builds
from app.internal_api import Api

from util.dockerhub import create_pending_repo
from util.github import create_github_repo

manager = Manager(app)


def setup_logging(log_file_path):
    logging.basicConfig(
        filename=log_file_path,
        # stream=sys.stdout,
        format='[%(asctime)s][%(name)s][%(levelname)6s]: %(message)s',
        level=logging.DEBUG
    )


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
    Run cdic task  like docker hub repo creation
    """
    def run(self):
        setup_logging("/tmp/cdic_async_tasks.log")

        api = Api()
        create_github_repo(api)
        create_pending_repo(api)

        run_builds()


manager.add_command("create_sqlite_file", CreateSqliteFileCommand())
manager.add_command("create_db", CreateDBCommand())
manager.add_command("drop_db", DropDBCommand())

manager.add_command("run_async_tasks", RunAsyncTasks())

if __name__ == '__main__':
    manager.run()
