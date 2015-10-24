# coding: utf-8
import datetime
from io import StringIO
import json
import os

import logging
from backports.typing import Iterable, List

from flask import abort
from flask_wtf import Form
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.query import Query
from sqlalchemy.sql import true, or_, false, and_
from sqlalchemy.orm.exc import NoResultFound

from .. import app, db, git_store


from ..util.github import GhClient
from ..constants import SourceType, EventType
from ..exceptions import PatchDockerfileException, FailedToFindProjectByDockerhubName, DockerHubQueryError
from ..models import Project, User
from .event_logic import create_project_event
# from ..forms.project import ProjectForm

log = logging.getLogger(__name__)


class ProjectLogic(object):

    @classmethod
    def get_project_by_id_safe(
            cls, project_id: int,
            hide_removed_project: bool=True) -> Project or None:

        try:
            project = cls.query_project_by_id(project_id).one()
        except NoResultFound:
            return None

        if hide_removed_project and project.delete_requested_on is not None:
            return None
        else:
            return project

    @classmethod
    def query_project_by_id(cls, project_id: int) -> Query:
        """
        :raises NoResultFound: when no such project exists
        """
        return Project.query.filter(Project.id == project_id)

    @classmethod
    def query_all_ready_projects(cls) -> Query:
        """
        :return: All projects which is not deleted and already have GH and DH repos ready
        """
        return (
            Project.query
            .filter(Project.github_repo_exists)
            .filter(Project.dockerhub_repo_exists)
            .filter(Project.delete_requested_on.is_(None))
        )

    @classmethod
    def get_projects_to_run_build_again(cls) -> List[Project]:
        delay = datetime.timedelta(600)  # seconds, todo: move to config
        old_enough = datetime.datetime.utcnow() - datetime.timedelta(delay)
        projects = (
            cls.query_all_ready_projects()
            .filter(Project.build_requested_on.is_not(None))
            .filter(Project.build_requested_on < old_enough)
            .filter(or_(
                Project.build_triggered_on.is_(None),
                Project.build_triggered_on < Project.build_requested_on
            ))
        ).all()
        return projects

    @classmethod
    def update_dockerfile(cls, project: Project, silent=True):
        update_patched_dockerfile(project)
        if not silent:
            build_event = create_project_event(
                project, "Started new build",
                data_json=json.dumps({"build_requested_dt": datetime.datetime.utcnow().isoformat()}),
                event_type=EventType.BUILD_REQUESTED
            )
            db.session.add(build_event)
        db.session.add(project)

    @classmethod
    def should_commit_changes(cls, p: Project):
        if p.patched_dockerfile_on is None:
            return False
        elif p.local_repo_changed_on is None:
            return True
        else:
            return p.patched_dockerfile_on > p.local_repo_changed_on

    @classmethod
    def should_push_changes(cls, p: Project):
        if p.local_repo_changed_on is None:
            return False
        elif p.local_repo_pushed_on is None:
            return True
        else:
            return p.local_repo_changed_on > p.local_repo_pushed_on

    @classmethod
    def should_send_build_trigger(cls, p: Project):
        if p.build_requested_on is None:
            return False
        elif p.local_repo_pushed_on is None:
            return False
        elif p.build_triggered_on is None:
            return True
        else:
            return p.build_triggered_on < p.build_requested_on



def get_all_projects_query() -> Query:
    return Project.query.order_by(Project.created_on.desc())


def get_projects_by_user(user: User) -> List[User]:
    """
    :param User user: user instance
    :return query to List[Project]: projects owned by `user`
    """
    return Project.query.filter(Project.user_id == user.id).all()


def get_project_by_title(user: User, title: str) -> Project:
    """
    :raises NoResultFound: when no such project exists
    """
    return Project.query.filter(Project.user_id == user.id).filter_by(title=title).one()

def get_project_by_id(ident: int) -> Project:
    """
    :raises NoResultFound: when no such project exists
    """
    return Project.query.get(ident)

def get_running_projects() -> List[Project]:
    return Project.query.filter(Project.build_is_running == true()).all()

def get_projects_to_create_dh() -> List[Project]:
    return (
        Project.query
        .filter(Project.github_repo_exists == true())
        .filter(Project.dockerhub_repo_exists == false())
        .filter(Project.delete_requested_on.is_(None))
    ).all()

def get_projects_to_update_dh_status() -> List[Project]:
    return [
        project for project in
        (Project.query
            .filter(Project.dockerhub_repo_exists == true())
            .filter(Project.delete_requested_on.is_(None))
            .filter(Project.local_repo_pushed_on.isnot(None)).all())
        if not project.is_dh_build_finished
    ]

def get_projects_to_start_dh_build() -> List[Project]:
    return (
        Project.query
        .filter(Project.dockerhub_repo_exists == true())
        .filter(Project.delete_requested_on.is_(None))
        .filter(or_(
            Project.dh_start_requested_on > Project.dh_start_done_on,
            and_(Project.dh_start_requested_on.isnot(None), Project.dh_start_done_on.is_(None)))
        )
    ).all()


def get_project_waiting_for_push() -> List[Project]:
    return (
        Project.query
        .filter(Project.build_is_running == true())  # just to be sure,
        # we write content to the file only after the  user press `Run Build`
        .filter(Project.github_repo_exists)
        .filter(Project.delete_requested_on.is_(None))
        .filter(Project.local_repo_changed_on.isnot(None))
        .filter(or_(
            Project.local_repo_pushed_on.is_(None),
            Project.local_repo_changed_on > Project.local_repo_pushed_on
        ))
    )


def exists_for_user(user: User, title: str) -> bool:
    try:
        get_project_by_title(user, title)
        return True
    except NoResultFound:
        return False


def add_project_from_form(user: User, form: Form) -> Project:
    if exists_for_user(user, form.title.data):
        abort(400)
    else:
        return Project(
            user=user,
            title=form.title.data,
            source_mode=form.source_mode.data,
        )


def update_project_from_form(project: Project, form: Form) -> Project:
    # todo: more complex logic after support of more source mode's
    project.local_text = form.local_text.data
    project.git_url = form.git_url.data
    return project


def path_dockerfile_for_project(project: Project, dockerfile: str=None) -> str:
    dockerfile = dockerfile or ""
    coprs_names = [lc.full_name for lc in project.linked_coprs]  # type: List[str]
    return patch_dockerfile(coprs_names, dockerfile)

BEGIN_CDIC_SECTION = ("### DOPR START, code until tag `DOPR END`"
                      " was auto-generated by dopr service\n\n")
END_CDIC_SECTION = "### DOPR END\n\n"


def patch_dockerfile(copr_names: Iterable[str], dockerfile: str) -> str:

    out = StringIO()
    before_from = True

    def write_copr_enabler():
        out.write(BEGIN_CDIC_SECTION)
        out.write("RUN yum install -y dnf dnf-plugins-core \\\n"
                  "    && mkdir -p /etc/yum.repos.d/\n")
        if copr_names:
            out.write("RUN ")

            out.write(" && \\\n    ".join([
                "dnf copr enable -y {}".format(copr)
                for copr in copr_names
            ]))
        # out.write("\n")
        # out.write("RUN dnf clean all\n")
        out.write("\n")
        out.write(END_CDIC_SECTION)

    for raw_line in dockerfile.split(os.linesep):
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("FROM"):
            if before_from:
                before_from = False
                out.write("{}\n".format(line))
                write_copr_enabler()
            else:
                raise PatchDockerfileException("Unexpected command, "
                                               "encountered FROM command twice")

        else:
            if before_from:
                raise PatchDockerfileException("Unexpected command, Dockerfile "
                                               "should start with FROM command")
            else:
                out.writelines("{}\n".format(line))
    return out.getvalue()


def update_patched_dockerfile(project: Project):
    # TODO: should be called auto-magically
    if project.source_mode == SourceType.LOCAL_TEXT:
        patched = path_dockerfile_for_project(project, project.local_text)
    else:
        raise NotImplementedError("Dockerfile patching for {} not implemented yet"
                                  .format(project.source_mode))

    project.patched_dockerfile = patched
    project.patched_dockerfile_on = datetime.datetime.utcnow()
    return project



def delete_project(project: Project):
    # 1. delete dockerhub repo, on success set dockerhub_repo_exist to None
    # 2. delete github, on success set dockerhub_repo_exist to None
    # 3. delete local git
    # 4. clean db

    log.info("Deleting project: {}".format(project.repo_name))
    if project.dockerhub_repo_exists:
        try:
            delete_dockerhub(project.repo_name)
        except DockerHubQueryError:
            log.exception("Failed to delete dockerhub: {}".format(project.repo_name))
            return
        project.dockerhub_repo_exists = False
        db.session.add(project)
        db.session.commit()

    if project.github_repo_exists:
        try:
            GhClient().delete_repo(project.repo_name)
        except Exception:
            log.exception("Failed to delete github repo: {}".format(project.repo_name))

        project.github_repo_exists = False
        db.session.add(project)
        db.session.commit()

    if project.local_repo_exists:
        git_store.clean(project.user.username, project.title)

        project.local_repo_exists = False
        db.session.add(project)
        db.session.commit()

    db.session.delete(project)
    db.session.commit()
    log.info("Delete project: {} done".format(project.repo_name))



def process_pending_deletes(*args, **kwargs):
    to_do = Project.query.filter(Project.delete_requested_on.isnot(None)).all()
    if not to_do:
        log.debug("No pending deletes")
        return
    for project in to_do:
        try:
            delete_project(project)
        except Exception:
            log.exception("Unhandled exception during project deletion")
