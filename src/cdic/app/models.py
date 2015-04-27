# coding: utf-8

import datetime


from sqlalchemy import UniqueConstraint


# VV todo: looks like it import DNS but py3 version should be dns
# from libravatar import libravatar_url

from . import constants
from . import db, app
# from . import helpers
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

    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    @property
    def name(self):
        """
        Return the short username of the user, e.g. bkabrda
        """
        return self.username

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

    created_on = db.Column(db.DateTime, default=db.func.now())
    updated_on = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

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

    @property
    def repo_name(self):
        return 'cdic-{}--{}'.format(self.user.username, self.title).lower()

    @property
    def github_repo_url(self):
        if not self.github_repo_exists:
            return None
        else:
            return "/".join([app.config["GITHUB_URL"], app.config["GITHUB_USER"],
                             self.repo_name])

    @property
    def dockerhub_repo_url(self):
        if not self.dockerhub_repo_exists:
            return None
        else:
            return "/".join([
                app.config["DOCKERREGISTRY_URL"],
                "u",
                app.config["DOCKERHUB_USERNAME"],
                self.repo_name
            ])

    @property
    def url_to_hub(self):
        return app.config["HUB_PROJECT_URL_TEMPLATE"].format(
            username=self.user.username, project_id=self.id)

    @property
    def dockerfile_preview(self) -> str:
        if self.source_mode != SourceType.LOCAL_TEXT:
            # todo: save to cache during build, and return when availble
            return ""
        else:
            return self.local_text or ""

    @property
    def recent_events(self):
        return self.history_events.order_by(ProjectEvent.created_on.desc())


class LinkedCopr(db.Model):

    __tablename__ = "linked_copr"

    id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    project = db.relationship("Project", backref=db.backref("linked_coprs", lazy="dynamic"))

    created_on = db.Column(db.DateTime, default=db.func.now())

    coprname = db.Column(db.String(120))
    username = db.Column(db.String(120))

    UniqueConstraint('project_id', 'username', 'coprname',  name='uix_1')

    @property
    def full_name(self):
        return "{}/{}".format(self.username, self.coprname)

    @property
    def copr_url(self):
        return "/".join([app.config["COPR_BASE_URL"], "coprs",
                        self.username, self.coprname])


class ProjectEvent(db.Model):

    __tablename__ = "project_event"

    id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(db.Integer, db.ForeignKey("project.id"))
    project = db.relationship("Project", backref=db.backref("history_events", lazy="dynamic"))

    created_on = db.Column(db.DateTime, default=db.func.now())

    human_text = db.Column(db.Text)

    optional_data_json = db.Column(db.Text)
    optional_event_type = db.Column(db.String(32))

