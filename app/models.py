# from app import db, ma
from app.extensions import db, ma


class EnrollmentTerm(db.Model):
    __tablename__ = 'enrollment_terms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    start_at = db.Column(db.DateTime)
    end_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime)
    workflow_state = db.Column(db.String)
    sis_term_id = db.Column(db.String)
    sis_import_id = db.Column(db.Integer)
    cut_off_date = db.Column(db.DateTime)

    current_term = db.Column(db.Boolean, server_default='false',
                             nullable=False)


class Record(db.Model):
    __tablename__ = 'records'
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime)
    term_id = db.Column(db.Integer)

    grades = db.relationship('Grade', backref='record')

    def __repr__(self):
        return str(self.id)


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    enrollment_term_id = db.Column(db.Integer,
                                   db.ForeignKey('enrollment_terms.id'))

    grades = db.relationship('Grade', backref='course')
    courses = db.relationship('CourseUserLink', backref='course')
    outcome_results = db.relationship('OutcomeResult', backref='course')

    @staticmethod
    def course_grades(course_id):
        stmt = db.text('''
            SELECT grade, cast( count(*) AS FLOAT)/cnt AS percent
            FROM 
                (SELECT u.id, COALESCE(left(g.grade, 1), 'N/A') AS GRADE, count(*) OVER() AS cnt
                FROM course_user_link cl
                    LEFT JOIN users u ON u.id = cl.user_id
                    LEFT JOIN grades g ON g.course_id = cl.course_id AND g.user_id = cl.user_id
                WHERE cl.course_id = :course_id) temp
            GROUP BY grade, cnt
            ORDER BY grade;
        ''')
        grades = db.session.execute(stmt, dict(course_id=course_id))
        return grades

    @staticmethod
    def outcome_stats(course_id):
        stmt = db.text('''
            SELECT title, id, max(cnt) max, min(cnt) min
            FROM
                (SELECT o.id, o.title title, count(*) cnt
                FROM outcome_results ores
                    JOIN outcomes o ON o.id = ores.outcome_id
                WHERE ores.course_id = :course_id
                GROUP BY ores.user_id, o.id, o.title) temp
            GROUP BY id, title
            ORDER BY max DESC;
        ''')
        results = db.session.execute(stmt, dict(course_id=course_id))
        return results

    def __repr__(self):
        return str(self.name)


class Grade(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    grade = db.Column(db.String)
    outcomes = db.Column(db.JSON)
    record_id = db.Column(db.Integer, db.ForeignKey('records.id'))
    threshold = db.Column(db.Numeric(asdecimal=False))
    min_score = db.Column(db.Numeric(asdecimal=False))

    def to_dict(self):
        '''
        Helper to return dictionary with the joined data included
        :return:
        '''
        d = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

        d['user'] = {k: v for k, v in self.user.__dict__.items() if
                     not k.startswith('_')}
        # del d['_sa_instance_state']
        # del d['user']['_sa_instance_state']

        return (d)

    def __repr__(self):
        return str(self.__dict__)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String)
    sis_user_id = db.Column(db.String)
    login_id = db.Column(db.String)

    grades = db.relationship('Grade', backref='user', lazy='dynamic')
    courses = db.relationship('CourseUserLink', backref='user')
    outcome_results = db.relationship('OutcomeResult', backref='user')

    def __repr__(self):
        return f'Name: {self.name}'


class OutcomeResult(db.Model):
    __tablename__ = 'outcome_results'
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Float)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    outcome_id = db.Column(db.Integer, db.ForeignKey('outcomes.id'))
    alignment_id = db.Column(db.String, db.ForeignKey('alignments.id'))
    submitted_or_assessed_at = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime)
    enrollment_term = db.Column(db.Integer)


class Outcome(db.Model):
    __tablename__ = 'outcomes'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    display_name = db.Column(db.String)
    calculation_int = db.Column(db.Integer)
    outcome_results = db.relationship('OutcomeResult', backref='outcome')

    def __repr__(self):
        return str(self.__dict__)


class Alignment(db.Model):
    __tablename__ = 'alignments'
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)

    outcome_results = db.relationship('OutcomeResult', backref='alignment')


class CourseUserLink(db.Model):
    __tablename__ = 'course_user_link'
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'),
                          primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                        primary_key=True)


class GradeCalculation(db.Model):
    __tablename__ = 'grade_calculation'
    id = db.Column(db.Integer, primary_key=True)
    grade_rank = db.Column(db.Integer, unique=True, nullable=False)
    grade = db.Column(db.String, nullable=False)
    threshold = db.Column(db.Float, nullable=False)
    min_score = db.Column(db.Float, nullable=False)


# JSON Serialization
class CourseSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'enrollment_term_id')


class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'sis_user_id', 'login_id')


class GradeSchema(ma.Schema):
    class Meta:
        fields = (
            'id', 'course_id', 'grade', 'record_id', 'user', 'threshold',
            'min_score')

    user = ma.Nested(UserSchema)


class OutcomeSchema(ma.ModelSchema):
    class Meta:
        fields = ('title', 'id', 'display_name')


class AlignmentSchema(ma.ModelSchema):
    class Meta:
        fields = ('id', 'name')


class OutcomeResultSchema(ma.ModelSchema):
    class Meta:
        model = OutcomeResult

    outcome = ma.Nested(OutcomeSchema)
    alignment = ma.Nested(AlignmentSchema)


class GradeCriteriaSchema(ma.ModelSchema):
    class Meta:
        # model = GradeCriteria
        fields = ('grade_rank', 'grade', 'threshold', 'min_score')


