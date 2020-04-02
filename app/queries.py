from app.models import GradeCriteria, GradeCriteriaSchema, EnrollmentTerm


def get_calculation_dictionaries():
    # calculation dictionaries
    calculation_dictionaries = GradeCriteria.query.order_by(
        GradeCriteria.grade_rank).all()
    grade_criteria_schema = GradeCriteriaSchema()
    calculation_dictionaries = grade_criteria_schema.dump(
        calculation_dictionaries, many=True)

    return calculation_dictionaries


def get_enrollment_term():
    term = EnrollmentTerm.query.filter(EnrollmentTerm.current_term).first()
    return term
