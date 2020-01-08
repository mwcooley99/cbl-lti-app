from app import db, ma


class Record(db.Model):
    __tablename__ = 'records'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime)
    term_id = db.Column(db.Integer)

    outcome_averages = db.relationship('OutcomeAverage', backref='record')
    grades = db.relationship('Grade', backref='record')

    def __repr__(self):
        return str(self.id)


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    enrollment_term_id = db.Column(db.Integer)

    outcome_averages = db.relationship('OutcomeAverage', backref='course')
    grades = db.relationship('Grade', backref='course')

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
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    grade = db.Column(db.String)
    outcomes = db.Column(db.JSON)
    record_id = db.Column(db.Integer, db.ForeignKey('records.id'))
    threshold = db.Column(db.Numeric)
    min_score = db.Column(db.Numeric)

    def __repr__(self):
        return str(self.__dict__)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    sis_user_id = db.Column(db.String)
    login_id = db.Column(db.String)

    grades = db.relationship('Grade', backref='user')

    def __repr__(self):
        return f'Name: {self.name}'


class GradeSchema(ma.Schema):
    class Meta:
        # Need to update with relevant fields
        fields = ('id', 'course_id', 'grade', 'outcomes')


class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'sis_user_id', 'login_id', 'grades')

    grades = ma.Nested(GradeSchema, many=True)

users = User.query.all()
user_schema = UserSchema()
user_schema.dump(users[5])

grades = Grade.query.limit(10)
grade_schema = GradeSchema()
grade_schema.dump(grades[3])

