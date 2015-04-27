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
from ..logic.copr_logic import create_link, get_link_by_id
from ..logic.project_logic import add_project_from_form, get_projects_by_user, \
    get_all_projects_query, get_project_by_id, update_project_from_form, create_project_event
from ..forms.copr import CoprSearchLinkForm

copr_bp = Blueprint("copr", __name__)


@copr_bp.route("/projects/<project_id>/link_coprs/", methods=["GET", "POST"])
@login_required
def search_and_link(project_id):
    project = get_project_by_id(int(project_id))

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
                db.session.add_all([cl, event])
                db.session.commit()
                # return redirect(url_for("main.project_details", project_id=project_id))
            else:
                form.copr_name.errors.append("That copr is already linked, "
                                             "probably you want to line another one?")

    return render_template("find_and_link_copr.html", project=project, form=form)

@copr_bp.route("/projects/<project_id>/link_coprs/<link_id>/delete")
@login_required
def unlink(project_id, link_id):
    link = get_link_by_id(link_id)
    if link:
        event = create_project_event(
            link.project,
            "Removed linked copr: {}/{}".format(link.username, link.coprname),
            data_json=json.dumps({"id": link.id, "username": link.username, "coprname": link.coprname}),
            event_type="removed_link")
        db.session.add(event)
        db.session.delete(link)
        db.session.commit()
    return redirect(url_for("copr.search_and_link", project_id=project_id))
