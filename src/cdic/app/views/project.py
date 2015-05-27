# coding: utf-8
import json
import logging

log = logging.getLogger(__name__)

from sqlalchemy.orm.exc import NoResultFound
from flask import Blueprint, request, abort, render_template, flash, g, redirect, url_for

from .. import db, app
from ..views.auth import login_required
from ..logic.user_logic import get_user_by_name
from ..logic.build_logic import schedule_build
from ..logic.project_logic import add_project_from_form, get_projects_by_user, \
    get_project_by_id, update_project_from_form, update_patched_dockerfile, get_project_by_title
from ..logic.event_logic import create_project_event
from ..forms.project import ProjectForm, ProjectCreateForm
from ..constants import EventType


project_bp = Blueprint("project", __name__)


@project_bp.route("/projects/<project_id>/start_build", methods=["GET"])
@login_required
def start_build(project_id):
    project = get_project_by_id(int(project_id))
    project.check_editable_by(g.user)
    if project.build_is_running:
        flash("Build request is already being processed, please wait", "danger")
        return redirect(url_for("project.details", username=project.user.username, title=project.title))

    schedule_build(project)
    flash("Build scheduled", "success")
    return redirect(url_for("project.details", username=project.user.username, title=project.title))


@project_bp.route("/users/<username>/")
def list_by_user(username):
    try:
        owner = get_user_by_name(username)
        return render_template(
            "project/list.html",
            owner=owner,
            my_prj_btn_active=True,
            project_list=get_projects_by_user(owner)
        )

    except NoResultFound:
        abort(404)


@project_bp.route("/projects/<project_id>/")
def details_by_id(project_id):
    project = get_project_by_id(int(project_id))
    return redirect(url_for("project.details", username=project.user.username, title=project.title))
    # return render_template("project/details.html", project=project)

@project_bp.route("/users/<username>/<title>/")
def details(username, title):
    user = get_user_by_name(username)
    project = get_project_by_title(user, title)
    return render_template("project/details.html", project=project)


@project_bp.route("/projects/add", methods=["GET"])
@login_required
def create_view(form=None):
    if not form:
        form = ProjectCreateForm()
    return render_template("project/add.html", form=form)


@project_bp.route("/projects/add", methods=["POST"])
@login_required
def create_handle():
    form = ProjectCreateForm()
    if form.validate_on_submit():
        project = add_project_from_form(g.user, form)
        project.local_text = "FROM fedora:latest \n"
        project.patched_dockerfile = ""
        event = create_project_event(project, "Created")
        db.session.add_all([project, event])
        db.session.commit()
        return redirect(url_for("project.details", username=project.user.username, title=project.title))
    else:
        return create_view(form=form)


@project_bp.route("/projects/edit/<project_id>", methods=["GET", "POST"])
@login_required
def edit(project_id):
    project = get_project_by_id(int(project_id))
    project.check_editable_by(g.user)

    form = ProjectForm(obj=project)

    if request.method == "POST" and form.validate_on_submit():
        old_source_mode = project.source_mode
        update_project_from_form(project, form)

        event = create_project_event(project, "Edited",
                                     data_json=json.dumps(form.data),
                                     event_type=EventType.PROJECT_EDITED)
        update_patched_dockerfile(project)
        db.session.add_all([project, event])
        db.session.commit()
        flash("Project was altered", "success")

        if old_source_mode == project.source_mode:
            # if not user should source fields
            return redirect(url_for("project.details", username=project.user.username, title=project.title))

    return render_template("project/edit.html", project=project, form=form)
