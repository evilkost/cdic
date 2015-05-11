# coding: utf-8
import datetime

import logging
import os

from .util.git import GitStore

from . import app, db
from .constants import SourceType
from .logic.project_logic import get_running_projects, get_project_waiting_for_push
from .logic.event_logic import create_project_event
from .models import Project


log = logging.getLogger(__name__)


def update_local_repo_and_push(project: Project):
    if project.source_mode == SourceType.LOCAL_TEXT:
        gs = GitStore(app.config["CDIC_WORKPLACE"])

        repo = gs.get_existing_repo(project.user.username, project.title)

        with open(os.path.join(repo.working_dir, "Dockerfile"), "w") as df:
            df.write(project.patched_dockerfile)

        gs.commit_changes(repo, ["Dockerfile"])
        gs.push_remote(repo)
        project.local_repo_pushed_on = datetime.datetime.utcnow()
        pe = create_project_event(project, "New version pushed to github")
        db.session.add_all([pe, project])

    else:
        raise NotImplementedError("Update of local repo for source: {} "
                                  "not implemented".format(project.source_mode))


def init_local_repo(project: Project):
    if project.source_mode == SourceType.LOCAL_TEXT:
        gs = GitStore(app.config["CDIC_WORKPLACE"])

        repo = gs.init_local(project.user.username, project.title)
        gs.add_remote(repo, project.github_push_url)
        open(os.path.join(repo.working_dir, "Dockerfile"), "wb").close()  # touch Dockerfile
        gs.initial_commit(repo, ["Dockerfile"])

        project.local_repo_exists = True

        pe = create_project_event(project, "Created local repo")
        db.session.add_all([pe, project])

    else:
        raise NotImplementedError("Init of local repo for source: {} "
                                  "not implemented".format(project.source_mode))


def build_one(project: Project):
    if not project.github_repo_exists:
        log.info("github repo doesn't exists for: {}".format(project.repo_name))
        # waiting for github repo creation
        return
    else:
        if not project.local_repo_exists:
            log.info("local repo doesn't exists for: {}".format(project.repo_name))
            init_local_repo(project)

        log.info("committing changes and pushing them for: {}".format(project.repo_name))
        update_local_repo_and_push(project)

        if project.dockerhub_repo_exists:
            # mark build as started
            project.build_is_running = False
            pe = create_project_event(
                project, "Build request passed to Dockerhub, wait for result")
            db.session.add_all([project, pe])

        db.session.commit()


def run_builds():
    # for prj in get_running_projects():
    for prj in get_project_waiting_for_push():
        try:
            log.info("Trying to push project: {} to github".format(prj.repo_name))
            build_one(prj)
        except Exception as err:
            log.exception("Error during build of prj: {}".format(prj))
    else:
        log.debug("No projects to push to github")
