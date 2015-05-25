# coding: utf-8
import json

from flask import Blueprint, request, render_template, redirect, url_for, g

# from werkzeug import check_password_hash, generate_password_hash
import logging


log = logging.getLogger(__name__)

from .. import db
from ..async.pusher import schedule_task
from ..views.auth import login_required
from ..logic.copr_logic import create_link, get_link_by_id
from ..logic.project_logic import get_project_by_id, update_patched_dockerfile
from ..logic.event_logic import create_project_event
from ..forms.copr import CoprSearchLinkForm
from ..logic.dockerhub_logic import update_dockerhub_build_status_task

copr_bp = Blueprint("copr", __name__)


@copr_bp.route("/projects/<project_id>/link_coprs/", methods=["GET", "POST"])
@login_required
def search_and_link(project_id):
    project = get_project_by_id(int(project_id))
    project.check_editable_by(g.user)
    form = CoprSearchLinkForm()

    if request.method == "POST" and form.validate_on_submit():
        if request.form["btn"] == "add_by_name":
            #TODO: add validator for {}/{} format

            (username, coprname) = form.copr_name.data.split("/")

            log.info("adding corp: {}/{} to project: {}".format(username, coprname, project.title))
            cl = create_link(project, username, coprname)
            if cl:
                event = create_project_event(project,
                                             "Linked copr: {}/{}".format(username, coprname),
                                             data_json=json.dumps(form.data),
                                             event_type="created_link")
                update_patched_dockerfile(project)
                db.session.add_all([cl, event, project])
                db.session.commit()
                # return redirect(url_for("project.details", project_id=project_id))
            else:
                form.copr_name.errors.append("That copr is already linked, "
                                             "probably you want to line another one?")

    return render_template("find_and_link_copr.html", project=project, form=form)

@copr_bp.route("/projects/<project_id>/link_coprs/<link_id>/delete")
@login_required
def unlink(project_id, link_id):
    link = get_link_by_id(link_id)
    if link:
        project = link.project
        project.check_editable_by(g.user)

        update_patched_dockerfile(project)

        event = create_project_event(
            link.project,
            "Removed linked copr: {}/{}".format(link.username, link.coprname),
            data_json=json.dumps({"id": link.id, "username": link.username, "coprname": link.coprname}),
            event_type="removed_link")
        db.session.add_all([project, event])
        db.session.delete(link)
        db.session.commit()
    return redirect(url_for("copr.search_and_link", project_id=project_id))

@copr_bp.route("/projects/<project_id>/update_build_history", methods=["GET", "POST"])
@login_required
def update_dh_history(project_id):
    # update_dockerhub_build_status(project_id)
    schedule_task(update_dockerhub_build_status_task, project_id)
    return redirect(url_for("project.details", project_id=project_id))
