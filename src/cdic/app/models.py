# coding: utf-8

import datetime



# VV todo: looks like it import DNS but py3 version should be dns
# from libravatar import libravatar_url

from . import constants
from . import db
# from . import helpers


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

    # TODO: automark time of user creation
    #dt_created =

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

    id = db.Column(db.Integer, primary_key=True)

    # owner
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    user = db.relationship("User", backref=db.backref("projects", lazy="dynamic"))

    # TODO:
    # dt_created =

    source_mode = db.Column(db.String(40))  # select what source option is used at the moment
    #  see .constants.SourceType
    local_text = db.Column(db.Text)
    git_url = db.Column(db.Text)

