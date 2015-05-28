# coding: utf-8
import json
import logging
import flask
from werkzeug.utils import redirect
from app.forms.copr import CoprSearchLinkForm
from app.logic.copr_logic import create_link, get_link_by_id
from app.logic.event_logic import create_project_event
from app.logic.project_logic import get_project_by_id, update_patched_dockerfile
from app.views.auth import login_required
# from app.views.copr import log

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

@project_bp.route("/users/<username>/<title>/")
def details(username, title):
    user = get_user_by_name(username)
    project = get_project_by_title(user, title)
    return render_template("project/details.html", project=project, project_info_page=True)


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

@project_bp.route("/users/<username>/<title>/start_build", methods=["GET", "POST"])
@login_required
def start_build(username, title):
    user = get_user_by_name(username)
    project = get_project_by_title(user, title)

    project.check_editable_by(g.user)
    if project.build_is_running:
        flash("Build request is already being processed, please wait", "danger")
        return redirect(url_for("project.details", username=project.user.username, title=project.title))

    schedule_build(project)
    flash("Build scheduled", "success")
    return redirect(url_for("project.details", username=project.user.username, title=project.title))



@project_bp.route("/users/<username>/<title>/edit", methods=["GET", "POST"])
@login_required
def edit(username, title):
    user = get_user_by_name(username)
    project = get_project_by_title(user, title)

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

    return render_template("project/edit.html", project=project, form=form, project_edit_page=True)


@project_bp.route("/users/<username>/<title>/link_coprs/", methods=["GET", "POST"])
@login_required
def search_and_link(username, title):
    user = get_user_by_name(username)
    project = get_project_by_title(user, title)
    form = CoprSearchLinkForm()

    if request.method == "POST" and form.validate_on_submit():
        if request.form["btn"] == "add_by_name":
            #TODO: add validator for {}/{} format

            (username, coprname) = form.copr_name.data.split("/")

            log.info("adding corp: {}/{} to project: {}".format(username, coprname, project.title))
            link = create_link(project, username, coprname)
            if link:
                event = create_project_event(project,
                                             "Linked copr: {}/{}".format(username, coprname),
                                             data_json=json.dumps(form.data),
                                             event_type="created_link")
                update_patched_dockerfile(project)
                db.session.add_all([link, event, project])
                db.session.commit()
                flask.flash("Copr {} was linked to {}"
                            .format(link.full_name, project.repo_name),
                            category="success")
            else:
                form.copr_name.errors.append("That copr is already linked, "
                                             "probably you want to line another one?")

    return render_template("project/find_and_link_coprs.html",
                           project=project, form=form, project_link_page=True)


@project_bp.route("/users/<username>/<title>/link_coprs/<link_id>/delete")
@login_required
def unlink(username, title, link_id):
    user = get_user_by_name(username)
    project = get_project_by_title(user, title)
    link = get_link_by_id(link_id)
    if link and link in project.linked_coprs:
        update_patched_dockerfile(project)
        event = create_project_event(
            link.project,
            "Removed linked copr: {}/{}".format(link.username, link.coprname),
            data_json=json.dumps({"id": link.id, "username": link.username, "coprname": link.coprname}),
            event_type="removed_link")
        db.session.add_all([project, event])
        db.session.delete(link)
        db.session.commit()
        flask.flash("Copr {} was unlinked from {}"
                    .format(link.full_name, project.repo_name),
                    category="success")
    return redirect(url_for("project.search_and_link",
                            username=project.user.username, title=project.title))
