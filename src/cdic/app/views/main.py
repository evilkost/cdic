# coding: utf-8
import json

from flask import Blueprint, request, abort, render_template, flash, g, redirect, url_for
# from werkzeug import check_password_hash, generate_password_hash

from sqlalchemy.orm.exc import NoResultFound
import logging



log = logging.getLogger(__name__)


from .. import db
# from ..util.dockerhub import get_builds_history
from ..views.auth import login_required
from ..logic.user_logic import get_user_by_name
from ..logic.project_logic import add_project_from_form, get_projects_by_user, \
    get_all_projects_query, get_project_by_id, update_project_from_form, update_patched_dockerfile
from ..logic.event_logic import create_project_event
from ..forms.project import ProjectForm
from ..constants import EventType


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html",
                           project_list=get_all_projects_query().limit(20),
                           home_btn_active=True)



