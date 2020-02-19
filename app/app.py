# -*- coding: utf-8 -*-
"""The app module, containing the app factory function."""
import logging
import sys

from flask import Flask, render_template

import app.settings as settings
from app import commands, \
    user  # Need to import modules that contain blueprints
from app.extensions import (
    db,
    ma
)


def create_app(config_object="app.settings.configClass"):
    """Create application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    config_object = settings.configClass
    app = Flask(__name__.split(".")[0])
    app.config.from_object(config_object)

    register_extensions(app)
    register_blueprints(app)
    register_errorhandlers(app)
    register_shellcontext(app)
    register_commands(app)
    configure_logger(app)
    register_filters(app)
    return app


def register_extensions(app):
    """Register Flask extensions."""

    db.init_app(app)
    ma.init_app(app)

    # Import models
    return None


def register_blueprints(app):
    """Register Flask blueprints."""
    # app.register_blueprint(public.views.blueprint)
    # app.register_blueprint(user.views.blueprint)
    # app.register_blueprint(launch.views.blueprint)
    app.register_blueprint(user.views.blueprint)
    return None


def register_errorhandlers(app):
    """Register error handlers."""

    def render_error(error):
        """Render error template."""
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, "code", 500)
        return render_template(f"{error_code}.html"), error_code

    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None


def register_shellcontext(app):
    """Register shell context objects."""
    pass

    def shell_context():
        """Shell context objects."""
        # TODO - move import...
        from app.models import Outcome, OutcomeAverage, Course, Record, Grade, \
            User, \
            UserSchema, GradeSchema, Alignment, OutcomeResult, CourseUserLink, \
            OutcomeSchema, OutcomeResultSchema, AlignmentSchema

        return dict(db=db, Outcome=Outcome, OutcomeAverage=OutcomeAverage,
                    Course=Course, Record=Record, Grade=Grade, User=User,
                    UserSchema=UserSchema, GradeSchema=GradeSchema,
                    Alignment=Alignment, OutcomeResult=OutcomeResult,
                    CourseUserLink=CourseUserLink,
                    OutcomeSchema=OutcomeSchema,
                    OutcomeResultSchema=OutcomeResultSchema,
                    AlignmentSchema=AlignmentSchema)

    app.shell_context_processor(shell_context)


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(commands.test)
    app.cli.add_command(commands.lint)


def configure_logger(app):
    """Configure loggers."""
    handler = logging.StreamHandler(sys.stdout)
    if not app.logger.handlers:
        app.logger.addHandler(handler)


def register_filters(app):
    @app.template_filter('strftime')
    def datetimeformat(value, format='%m-%d-%Y'):
        return value.strftime(format)
