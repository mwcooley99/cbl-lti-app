from app.models import GradeCriteriaSchema, EnrollmentTerm, GradeCalculation


def get_calculation_dictionaries():
    # calculation dictionaries
    calculation_dictionaries = GradeCalculation.query.order_by(
        GradeCalculation.grade_rank
    ).all()
    grade_criteria_schema = GradeCriteriaSchema()
    calculation_dictionaries = grade_criteria_schema.dump(
        calculation_dictionaries, many=True
    )
    # calculation_dictionaries = {}
    return calculation_dictionaries


def get_enrollment_term():
    term = EnrollmentTerm.query.filter(EnrollmentTerm.current_term).first()

    # Check to see if a current term has been chosen
    if term:
        return term
    # if it hasn't, return the default term
    else:
        return EnrollmentTerm.query.filter(EnrollmentTerm.id == 1).first()
