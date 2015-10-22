# coding: utf-8

from flask import Blueprint, render_template
# from werkzeug import check_password_hash, generate_password_hash

import logging
log = logging.getLogger(__name__)


from ..logic.project_logic import get_all_projects_query

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html",
                           project_list=get_all_projects_query().limit(20),
                           home_btn_active=True)
