# coding: utf-8

from .. import db, git_store
import datetime
import os
from ..constants import SourceType
from ..models import Project

from .event_logic import create_project_event


class GhLogic(object):

    @classmethod
    def update_local_repo(cls, project: Project):
        if project.source_mode == SourceType.LOCAL_TEXT:

            repo = git_store.get_existing_repo(project.user.username, project.title)

            with open(os.path.join(repo.working_dir, "Dockerfile"), "w") as df:
                df.write(project.patched_dockerfile)

            with open(os.path.join(repo.working_dir, "README.md"), "w") as handle:
                handle.write(project.readme_content)

            git_store.commit_changes(repo, ["Dockerfile", "README.md"])
            project.local_repo_changed_on = datetime.datetime.utcnow()
            pe = create_project_event(project, "Changes are committed to the local git")
            db.session.add_all([pe, project])

        else:
            raise NotImplementedError("Update of local repo for source mode: {} "
                                      "not implemented".format(project.source_mode))

    @classmethod
    def push_changes(cls, project: Project):
        repo = git_store.get_existing_repo(project.user.username, project.title)
        git_store.push_remote(repo)
        project.local_repo_pushed_on = datetime.datetime.utcnow()
        pe = create_project_event(project, "New version pushed to github")
        db.session.add_all([pe, project])

    @classmethod
    def set_github_repo_created(cls, project: Project):
        if not project.github_repo_exists:
            project.github_repo_exists = True

            pe = create_project_event(project, "Created github repo")
            db.session.add_all([project, pe])

    @classmethod
    def set_github_repo_deleted(cls, project: Project):
        project.github_repo_exists = False

        pe = create_project_event(project, "Deleted github repo")
        db.session.add_all([project, pe])
