from app import db
from datetime import datetime


# print(db.Model.metadata.tables['records'])
#
class Record(db.Model):
    # __table__ = db.Model.metadata.tables['records']
    __tablename__ = 'records'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime)
    term_id = db.Column(db.Integer)

    outcome_averages = db.relationship('OutcomeAverage', backref='record')

    def __repr__(self):
        return str(self.id)


class Course(db.Model):
    # __table__ = db.Model.metadata.tables['courses']
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    enrollment_term_id = db.Column(db.Integer)

    outcome_averages = db.relationship('OutcomeAverage', backref='course')

    def __repr__(self):
        return str(self.name)


class OutcomeAverage(db.Model):
    # __table__ = db.Model.metadata.tables['outcome_averages']
    __tablename__ = 'outcome_averages'
    id = db.Column(db.Integer, primary_key=True)
    outcome_avg = db.Column(db.Float)
    user_id = db.Column(db.Integer)
    outcome_id = db.Column(db.Integer, db.ForeignKey('outcomes.id'))
    record_id = db.Column(db.Integer, db.ForeignKey('records.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    def __repr__(self):
        return str(self.__dict__)


class Outcome(db.Model):
    # __table__ = db.Model.metadata.tables['outcomes']
    __tablename__ = 'outcomes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    display_name = db.Column(db.String)
    outcome_averages = db.relationship('OutcomeAverage', backref='outcome')

    def __repr__(self):
        return str(self.__dict__)
