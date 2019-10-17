from app import db


class Record(db.Model):
    __tablename__ = 'records'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime)
    term_id = db.Column(db.Integer)

    outcome_averages = db.relationship('OutcomeAverage', backref='record')

    def __repr__(self):
        return str(self.id)


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    enrollment_term_id = db.Column(db.Integer)

    outcome_averages = db.relationship('OutcomeAverage', backref='course')

    def __repr__(self):
        return str(self.name)


class OutcomeAverage(db.Model):
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
    __tablename__ = 'outcomes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    display_name = db.Column(db.String)
    outcome_averages = db.relationship('OutcomeAverage', backref='outcome')

    def __repr__(self):
        return str(self.__dict__)


class Grade(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer)
    grade = db.Column(db.String)
    outcomes = db.Column(db.JSON)
