# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from flask import flash
from app.models import EnrollmentTerm


def flash_errors(form, category="warning"):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text} - {error}", category)


def get_enrollment_term():
    term = EnrollmentTerm.query.filter(EnrollmentTerm.current_term).first()
    return term
