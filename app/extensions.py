# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located in app.py."""

from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_admin import Admin


db = SQLAlchemy()
ma = Marshmallow()
migrate = Migrate()
admin = Admin(template_mode="bootstrap3")
