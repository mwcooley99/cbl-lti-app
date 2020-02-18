# -*- coding: utf-8 -*-
"""User views."""
from flask import Blueprint, render_template


blueprint = Blueprint("user", __name__, url_prefix="/user", static_folder="../static")


@blueprint.route("/")
def members():
    """List members."""
    return render_template("index.html")
