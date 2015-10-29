# coding: utf-8

import datetime
from typing import Iterable

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy_utils import ArrowType
import arrow


# VV todo: looks like it import DNS but py3 version should be dns
# from libravatar import libravatar_url

from . import constants
from . import db, app
# from . import helpers
from .exceptions import AccessRejected
from .constants import SourceType


class User(db.Model):
    """
    Represents user of the copr frontend
    """
    __tablename__ = "user"

    # PK;  TODO: the 'username' could be also PK
    id = db.Column(db.Integer, primary_key=True)

    # unique username
    username = db.Column(db.String(100), nullable=False, unique=True)

    # email
    mail = db.Column(db.String(150), nullable=False)

    # optional timezone
    timezone = db.Column(db.String(50), nullable=True)

    created_on = db.Column(ArrowType, default=arrow.utcnow())
    updated_on = db.Column(ArrowType, default=arrow.utcnow(), onupdate=arrow.utcnow())

    @property
    def name(self) -> str:
        """
        Return the short username of the user, e.g. bkabrda
        """
        return self.username

    @property
    def fas_url(self) -> str:
        return app.config["FAS_USER_URL_TEMPLATE"].format(self.username)
    # @property
    # def gravatar_url(self):
    #     """
    #     Return url to libravatar image.
    #     """
    #
    #     try:
    #         return libravatar_url(email=self.mail, https=True)
    #     except IOError:
    #         return ""


class ProjectEvent(db.Model):

    __tablename__ = "project_event"

    id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    project = db.relationship("Project", backref=db.backref("history_events", lazy="dynamic"))

    created_on = db.Column(ArrowType, default=arrow.utcnow())

    human_text = db.Column(db.Text)

    optional_data_json = db.Column(db.Text)
    optional_event_type = db.Column(db.String(32))


class Project(db.Model):
    """
    Each projects contains base Dockerfile (as stored text or link to repo[only git for now])
    and so number of enabled copr repos.
    """
    __tablename__ = "project"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120))

    # owner
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref=db.backref("projects", lazy="dynamic"))

    created_on = db.Column(ArrowType, default=arrow.utcnow())
    updated_on = db.Column(ArrowType, default=arrow.utcnow(), onupdate=arrow.utcnow())

    build_requested_on = db.Column(ArrowType)  # time, when the user requested new build
    build_triggered_on = db.Column(ArrowType)  # time, when the service invoked dockerhub build trigger

    # this variable define only "local" build process, after the user click on "Run build" and until
    # we push changes to github or create docker hub (for the first build)
    # build_is_running = db.Column(db.Boolean, default=False)
    local_repo_exists = db.Column(db.Boolean, default=False)
    patched_dockerfile = db.Column(db.Text)
    patched_dockerfile_on = db.Column(ArrowType)

    # build_started_on = db.Column(db.DateTime)
    local_repo_changed_on = db.Column(ArrowType)
    local_repo_pushed_on = db.Column(ArrowType)

    source_mode = db.Column(db.String(40), default=SourceType.LOCAL_TEXT,
                            server_default=SourceType.LOCAL_TEXT)
    #  see .constants.SourceType
    local_text = db.Column(db.Text)
    git_url = db.Column(db.Text)
    # todo: later: git_source_sub_path, default "" // extract only sub dir
    # todo: git_source_branch, default "master"
    # todo: git_source_last_updated = db.Column(db.Boolean, nullable=True

    github_repo_exists = db.Column(db.Boolean, default=False)
    dockerhub_repo_exists = db.Column(db.Boolean, default=False)
    dh_build_trigger_url = db.Column(db.Text)

    # set on delete requests, indicates that project going to be deleted
    delete_requested_on = db.Column(ArrowType, index=True)

    def is_build_request_in_progress(self) -> bool:
        if self.build_requested_on is None:
            return False
        elif self.build_triggered_on is None:
            return True
        else:
            return self.build_requested_on > self.build_triggered_on

    def is_editable_by(self, user: User) -> bool:
        return self.user.id == user.id

    def check_editable_by(self, user: User) -> None:
        if not self.is_editable_by(user):
            raise AccessRejected("User `{}` doesn't have rights to edit project `{}`"
                                 .format(user.username, self.repo_name))

    @property
    def readme_content(self) -> str:
        return app.config["README_TEMPLATE"].format(**{
            "project_owner": self.user.name,
            "project_owner_url": self.user.fas_url,
        })

    @property
    def docker_pull_snippet(self) -> str:
        return "docker pull {}/{}:latest".format(
            app.config["DOCKERHUB_USERNAME"], self.repo_name)

    @property
    def ready_to_run(self):
        if not all([self.github_repo_exists, self.dh_build_trigger_url]):
            return False
        else:
            return not self.is_build_request_in_progress()

    # older methods
    @property
    def is_runnable(self) -> bool:
        if not self.build_is_running and self.patched_dockerfile:
            return True
        return False

    @property
    def repo_name(self) -> str:
        return '{}-{}'.format(self.user.username, self.title).lower()

    @property
    def github_repo_url(self) -> str:
        if not self.github_repo_exists:
            return None
        else:
            return "/".join([app.config["GITHUB_URL"], app.config["GITHUB_USER"],
                             str(self.repo_name)])

    @property
    def github_push_url(self) -> str:
        if not self.github_repo_exists:
            return None
        else:
            return "{}:{}/{}".format(
                app.config["GITHUB_PUSH_URL"],
                app.config["GITHUB_USER"],
                self.repo_name
            )

    @property
    def dockerhub_repo_url(self) -> str:
        if not self.dockerhub_repo_exists:
            return None
        else:
            return "/".join([
                app.config["DOCKERREGISTRY_URL"],
                "u",
                app.config["DOCKERHUB_USERNAME"],
                str(self.repo_name)
            ])

    @property
    def url_to_hub(self) -> str:
        return app.config["HUB_PROJECT_URL_TEMPLATE"].format(repo_name=self.repo_name)

    @property
    def recent_events(self) -> Iterable[ProjectEvent]:
        return self.history_events.order_by(ProjectEvent.created_on.desc())

    @property
    def should_start_dh_build(self) -> bool:
        if self.dh_start_requested_on:
            if not self.dh_start_done_on or \
                    self.dh_start_done_on < self.dh_start_requested_on:
                return True
        return False


class DhBuildInfo(db.Model):

    __tablename__ = "dh_build_info"

    id = db.Column(db.String(127), primary_key=True)

    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    project = db.relationship("Project", backref=db.backref("builds_info", lazy="dynamic"))

    fetched_on = db.Column(ArrowType, default=arrow.utcnow)

    status = db.Column(db.String(31))
    status_updated_on = db.Column(ArrowType, default=arrow.utcnow)

    details = db.Column(JSON)


def get_copr_url(username: str, coprname: str) -> str:
    return "/".join([app.config["COPR_BASE_URL"], "coprs", username, coprname])


class LinkedCopr(db.Model):

    __tablename__ = "linked_copr"

    id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    project = db.relationship("Project", backref=db.backref("linked_coprs", lazy="dynamic"))

    created_on = db.Column(ArrowType, default=arrow.utcnow())

    coprname = db.Column(db.String(120))
    username = db.Column(db.String(120))

    UniqueConstraint('project_id', 'username', 'coprname',  name='uix_1')

    @property
    def full_name(self) -> str:
        return "{}/{}".format(self.username, self.coprname)

    @property
    def copr_url(self) -> str:
        return get_copr_url(self.username, self.coprname)
