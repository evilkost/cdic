# coding: utf-8

from flask import Blueprint, g, request, render_template, flash, g, session, redirect, url_for
# from werkzeug import check_password_hash, generate_password_hash

from app import db


main_bp = Blueprint("main", __name__, url_prefix="/")


@main_bp.route("/")
def index():
    return render_template("index.html")
