# coding: utf-8
import datetime
import logging

from requests import post

from .. import db
from ..models import Project

from ..logic.event_logic import create_project_event

log = logging.getLogger(__name__)


class DhLogic(object):

    @classmethod
    def trigger_build(cls, p: Project):
        url = p.dh_build_trigger_url
        log.info("Going to trigger build for: {}".format(p.repo_name))
        post(url)
        p.build_triggered_on = datetime.datetime.utcnow()
        pe = create_project_event(p, "Build request was sent to the Dockerhub")
        db.session.add_all([p, pe])

        # todo: send action

    @classmethod
    def set_dh_created(cls, p: Project):
        p.dockerhub_repo_exists = True
        pe = create_project_event(p, "Created dockerhub automated build")
        db.session.add_all([p, pe])

    @classmethod
    def set_dh_deleted(cls, p: Project):
        p.dockerhub_repo_exists = False
        pe = create_project_event(p, "Deleted dockerhub automated build")
        db.session.add_all([p, pe])

    @classmethod
    def set_build_trigger(cls, p: Project, trigger: str):
        p.dh_build_trigger_url = trigger
        pe = create_project_event(p, "Obtained dh build trigger")
        db.session.add_all([p, pe])
