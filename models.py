from app import db
from datetime import datetime


class Record(db.Model):
    __table__ = db.Model.metadata.tables['records']

    def __repr__(self):
        return str(self.id)


class Course(db.Model):
    __table__ = db.Model.metadata.tables['courses']

    def __repr__(self):
        return str(self.name)


class Outcome_Average(db.Model):
    __table__ = db.Model.metadata.tables['outcome_averages']

    def __repr__(self):
        return str(self.outcome_id)


class Outcome(db.Model):
    __table__ = db.Model.metadata.tables['outcomes']

    def __repr__(self):
        return str(self.title)

    # __tablename__ = 'records'
    # id = db.Column(db.Integer, primary_key=True),
    # created_at = db.Column(db.DateTime, nullable=False),
    # term_id = db.Column(db.Integer)
#
# Records = Table('records', metadata,
#                 # Column('id', Integer, primary_key=True),
#                 Column('created_at', DateTime),
#                 Column('term_id', Integer),
#
#                 )
#
# OutcomeAverages = Table('outcome_averages', metadata,
#                         # Column('id', Integer, primary_key=True),
#                         Column('user_id', Integer),
#                         Column('outcome_id', Integer),
#                         Column('record_id', Integer, ForeignKey('Records.id')),
#                         Column('outcome_avg', Float),
#                         Column('course_id', Integer)
#                         )
#
# Courses = Table('courses', metadata,
#                 Column('id', Integer, primary_key=True),
#                 Column('name', String),
#                 Column('enrollment_term_id', Integer))
#
# Outcomes = Table('outcomes', metadata,
#                  Column('id', Integer, primary_key=True),
#                  Column('title', String),
#                  Column('display_name', String))
