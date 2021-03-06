from sqlalchemy import (
    create_engine,
    Integer,
    String,
    Table,
    Column,
    MetaData,
    ForeignKey,
    DateTime,
    Float,
    JSON,
    Boolean,
)
from sqlalchemy.ext.automap import automap_base
from app.config import configuration

import os

config = configuration[os.getenv("PULL_CONFIG")]

engine = create_engine(config.SQLALCHEMY_DATABASE_URI)

# reflect the tables
metadata = MetaData()
metadata.bind = engine

# automap base
Base = automap_base()
Base.prepare(engine, reflect=True)


EnrollmentTerms = Base.classes.enrollment_terms.__table__
GradeCalculation = Base.classes.grade_calculation.__table__
CanvasApiToken = Base.classes.canvas_api_tokens.__table__


Records = Table(
    "records",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("created_at", DateTime),
    Column("term_id", Integer),
)

Courses = Table(
    "courses",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("enrollment_term_id", Integer),
)

Grades = Table(
    "grades",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer),
    Column("course_id", Integer, ForeignKey("courses.id")),
    Column("grade", String),
    Column("outcomes", JSON),
    Column("record_id", Integer),
    Column("threshold", Float),
    Column("min_score", Float),
)

Users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("sis_user_id", String),
    Column("login_id", String),
)

OutcomeResults = Table(
    "outcome_results",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("score", Float),
    Column("course_id", Integer, nullable=False),
    Column("user_id", Integer, nullable=False),
    Column("outcome_id", Integer, nullable=False),
    Column("alignment_id", String, nullable=False),
    Column("submitted_or_assessed_at", DateTime, nullable=False),
    Column("last_updated", DateTime, nullable=False),
    Column("enrollment_term", Integer),
    Column("dropped", Boolean),
)

Alignments = Table(
    "alignments",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
)

Outcomes = Table(
    "outcomes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String, nullable=False),
    Column("display_name", String),
    Column("calculation_int", Integer, nullable=False),
)

CourseUserLink = Table(
    "course_user_link",
    metadata,
    Column("course_id", ForeignKey("courses.id"), primary_key=True, nullable=False),
    Column("user_id", ForeignKey("users.id"), primary_key=True, nullable=False),
)
