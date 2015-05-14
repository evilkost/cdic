# coding: utf-8

from sqlalchemy.sql import true, false

from .. import db
from ..models import Project

from .project_logic import get_project_by_id
from .event_logic import create_project_event


def get_pending_docker_create_repo_list() -> "Iterable[Project]":
    return (
        Project.query
        .filter(Project.github_repo_exists == true())
        .filter(Project.dockerhub_repo_exists == false())
    )


def set_docker_repo_created(ident: int):
    prj = get_project_by_id(ident)
    prj.dockerhub_repo_exists = True

    pe = create_project_event(prj, "Created dockerhub automated build")

    if prj.build_is_running:
        # first ever build,
        pe2 = create_project_event(prj, "Build request passed to Dockerhub, wait for result")
        db.session.add(pe2)
        prj.build_is_running = False

    db.session.add_all([prj, pe])
    db.session.commit()
