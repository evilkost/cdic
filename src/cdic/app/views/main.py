# coding: utf-8
import datetime
import json
from pprint import pprint

from flask import Blueprint, g, request, abort, render_template, flash, g, session, redirect, url_for
# from werkzeug import check_password_hash, generate_password_hash
import requests
from sqlalchemy.orm.exc import NoResultFound
import logging


log = logging.getLogger(__name__)

from cdic.util.dockerhub import get_builds_history

from .. import db
from ..internal_api import Api
from ..views.auth import login_required
from ..logic.user_logic import get_user_by_name
from ..logic.project_logic import add_project_from_form, get_projects_by_user, \
    get_all_projects_query, get_project_by_id, update_project_from_form, update_patched_dockerfile, \
    get_project_by_dockerhub_name
from ..logic.event_logic import create_project_event
from ..forms.project import ProjectForm
from ..constants import EventType


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
    # TODO: VALIDATE TITLE TO BE STRICTLY ALPHANUMERICAL
    log.warn("TODO: VALIDATE TITLE TO BE STRICTLY ALPHANUMERICAL")
    form = ProjectForm()
    if form.validate_on_submit():
        project = add_project_from_form(g.user, form)
        project.local_text = "FROM fedora:latest \n"
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
        update_patched_dockerfile(project)
        db.session.add_all([project, event])
        db.session.commit()
        flash("Project was altered", "success")

        if old_source_mode == project.source_mode:
            # if not user should source fields
            return redirect(url_for("main.project_details", project_id=project.id))

    return render_template("project_edit.html", project=project, form=form)


@main_bp.route("/projects/<project_id>/start_build", methods=["GET"])
@login_required
def project_start_build(project_id):
    project = get_project_by_id(int(project_id))
    if project.build_is_running:
        flash("Build request is already being processed, please wait", "danger")
        return redirect(url_for("main.project_details", project_id=project.id))

    project.build_is_running = True
    project.build_started_on = datetime.datetime.utcnow()
    update_patched_dockerfile(project)

    build_event = create_project_event(
        project, "Started new build",
        data_json=json.dumps({"build_requested_dt": datetime.datetime.utcnow().isoformat()}),
        event_type=EventType.BUILD_REQUESTED
    )

    db.session.add_all([project, build_event])
    db.session.commit()
    flash("Build started", "success")
    return redirect(url_for("main.project_details", project_id=project.id))


@main_bp.route("/hooks/dockerhub/", methods=["POST"])
def dockerhub_web_hook():
    try:
        # data = json.loads(request.data.decode("utf-8"))
        data = request.json
    except Exception as err:
        log.exception(err)
        return str(err), 400

    docker_name = data["repository"]["name"]
    project = get_project_by_dockerhub_name(docker_name)

    try:
        # todo: should spawn a celery task
        docker_builds = get_builds_history(Api(), project.repo_name)
        if docker_builds:
            docker_builds.sort(key=lambda x: x["created_on"])
            build_info = docker_builds[-1]
            project.dockerhub_build_status = build_info["status"]
            project.dockerhub_build_status_updated_on = build_info["updated_on"]
            db.session.add(create_project_event(project, "Updated docker build status"))

    except Exception as err:
        log.exception("Failed to get build history from Dockerhub")

    pe = create_project_event(
        project, "Received web hook request",
        data_json=json.dumps(data), event_type=EventType.WEBHOOK_CALLED
    )

    db.session.add_all([pe, project])
    db.session.commit()

    target_url = url_for("main.project_details", project_id=project.id, _external=True)
    requests.post(
        url=data["callback_url"],
        data=json.dumps(
            {
                "state": "success",
                "description": "build info updated",
                "context": "Copr Docker Image Composer",
                "target_url": target_url
            }
        )
    )
    return "Ok", 200
