# coding: utf-8
import datetime

import logging
import os

from .util.git import AnotherRepoExists

from . import app, db, git_store
from .constants import SourceType
from .logic.event_logic import create_project_event
from .models import Project


log = logging.getLogger(__name__)


def update_local_repo_and_push(project: Project):
    if project.source_mode == SourceType.LOCAL_TEXT:

        repo = git_store.get_existing_repo(project.user.username, project.title)

        with open(os.path.join(repo.working_dir, "Dockerfile"), "w") as df:
            df.write(project.patched_dockerfile)

        with open(os.path.join(repo.working_dir, "README.md"), "w") as handle:
            handle.write(project.readme_content)

        git_store.commit_changes(repo, ["Dockerfile", "README.md"])
        git_store.push_remote(repo)
        project.local_repo_pushed_on = datetime.datetime.utcnow()
        pe = create_project_event(project, "New version pushed to github")
        db.session.add_all([pe, project])

    else:
        raise NotImplementedError("Update of local repo for source mode: {} "
                                  "not implemented".format(project.source_mode))


def init_local_repo(project: Project):
    if project.source_mode == SourceType.LOCAL_TEXT:
        # git_store = GitStore(app.config["CDIC_WORKPLACE"])

        try:
            repo = git_store.init_local(project.user.username, project.title)
        except AnotherRepoExists:
            return

        git_store.add_remote(repo, project.github_push_url)
        open(os.path.join(repo.working_dir, "Dockerfile"), "wb").close()  # touch Dockerfile
        git_store.initial_commit(repo, ["Dockerfile"])

        project.local_repo_exists = True

        pe = create_project_event(project, "Created local repo")
        db.session.add_all([pe, project])

    else:
        raise NotImplementedError("Init of local repo for source mode: {} "
                                  "not implemented".format(project.source_mode))


def push_build(project: Project):
    if not project.local_repo_exists:
        log.info("Local repo doesn't exists for: {}".format(project.repo_name))
        init_local_repo(project)

    log.info("Committing changes and pushing them for: {}".format(project.repo_name))
    update_local_repo_and_push(project)
    db.session.commit()
