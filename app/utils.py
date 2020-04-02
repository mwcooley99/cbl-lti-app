# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from flask import flash
from app.models import EnrollmentTerm


def flash_errors(form, category="warning"):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text} - {error}", category)


