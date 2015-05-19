# coding: utf-8

from sqlalchemy.sql import true, false

from .. import db
from ..util.dockerhub import create_dockerhub_automated_build_repo
from ..models import Project
from ..logic.event_logic import create_project_event
from ..logic.project_logic import get_project_by_id
from ..async.task import OnDemandTask
from ..async.pusher import PREFIX, ctx_wrapper


def get_pending_docker_create_repo_list() -> "Iterable[Project]":
    return (
        Project.query
        .filter(Project.github_repo_exists == true())
        .filter(Project.dockerhub_repo_exists == false())
    )


def set_docker_repo_created(project: Project):
    project.dockerhub_repo_exists = True

    pe = create_project_event(project, "Created dockerhub automated build")
    if project.build_is_running:
        # first ever build,
        pe2 = create_project_event(project, "Build request passed to Dockerhub, wait for result")
        db.session.add(pe2)
        project.build_is_running = False

    db.session.add_all([project, pe])


def create_dockerhub_repo(project_id):
    project = get_project_by_id(project_id)
    create_dockerhub_automated_build_repo(project.repo_name)
    set_docker_repo_created(project)
    db.session.commit()


create_dockerhub_task = OnDemandTask(
    "crate dockerhub automated build",
    "{}_create_dockerhub".format(PREFIX),
    fn=ctx_wrapper(create_dockerhub_repo)
)
