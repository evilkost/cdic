# coding: utf-8
import json

from flask import Blueprint, g, request, abort, render_template, flash, g, session, redirect, url_for
# from werkzeug import check_password_hash, generate_password_hash
from sqlalchemy.orm.exc import NoResultFound
import logging

log = logging.getLogger(__name__)

from .. import db
from ..views.auth import login_required
from ..logic.user_logic import get_user_by_name
from ..logic.project_logic import add_project_from_form, get_projects_by_user, \
    get_all_projects_query, get_project_by_id, update_project_from_form, create_project_event
from ..forms.project import ProjectForm

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html",
                           project_list=get_all_projects_query().limit(20),
                           home_btn_active=True)


@main_bp.route("/users/<username>/")
def project_list(username):
    try:
        owner = get_user_by_name(username).one()
        return render_template(
            "project_list.html",
            owner=owner,
            my_prj_btn_active=True,
            project_list=get_projects_by_user(owner)
        )

    except NoResultFound:
        abort(404)


@main_bp.route("/projects/<project_id>/")
def project_details(project_id):
    project = get_project_by_id(int(project_id))
    return render_template("project_details.html", project=project)


@main_bp.route("/projects/add", methods=["GET"])
@login_required
def project_create_view(form=None):
    if not form:
        form = ProjectForm()
    return render_template("project_add.html", form=form)


@main_bp.route("/projects/add", methods=["POST"])
@login_required
def project_create_handle():
    form = ProjectForm()
    if form.validate_on_submit():
        project = add_project_from_form(g.user, form)
        event = create_project_event(project, "Created")
        db.session.add_all([project, event])
        db.session.commit()
        return redirect(url_for("main.project_details", project_id=project.id))
    else:
        return project_create_view(form=form)


@main_bp.route("/projects/edit/<project_id>", methods=["GET", "POST"])
@login_required
def project_edit(project_id):
    project = get_project_by_id(int(project_id))
    form = ProjectForm(obj=project)

    if request.method == "POST" and form.validate_on_submit():
        old_source_mode = project.source_mode
        update_project_from_form(project, form)

        event = create_project_event(project, "Edited",
                                     data_json=json.dumps(form.data),
                                     event_type="edited")

        db.session.add_all([project, event])
        db.session.commit()
        if old_source_mode == project.source_mode:
            # if not user should source fields
            return redirect(url_for("main.project_details", project_id=project.id))

    return render_template("project_edit.html", project=project, form=form)

