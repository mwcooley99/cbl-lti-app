import math

def calculate_traditional_grade(scores):
    # check if the outcome is assessed.
    if len(scores) == 0 or scores[0] == -1:
        return {
            'grade': 'n/a',
            'threshold': 'n/a',
            'min_score': 'n/a',
        }


    calculation_dictionaries = [
        {
            'grade': 'A',
            'threshold': 3.5,
            'min_score': 3
        },
        {
            'grade': 'A-',
            'threshold': 3.5,
            'min_score': 2.5
        },
        {
            'grade': 'B+',
            'threshold': 3,
            'min_score': 2.5
        },
        {
            'grade': 'B',
            'threshold': 3,
            'min_score': 2.25
        },
        {
            'grade': 'B-',
            'threshold': 3,
            'min_score': 2
        },
        {
            'grade': 'C',
            'threshold': 2.5,
            'min_score': 2
        },
        {
            'grade': 'I',
            'threshold': 0,
            'min_score': 0
        }
    ]

    scores_sorted = sorted(scores, reverse=True)
    threshold_index = math.ceil(0.75 * len(scores_sorted)) - 1


    threshold_score = scores_sorted[threshold_index]
    min_score = scores_sorted[-1]
    traditional_grade = dict(
        threshold=threshold_score,
        min_score=min_score
    )

    for grade in calculation_dictionaries:
        if threshold_score >= grade['threshold'] and min_score >= grade[
            'min_score']:
            traditional_grade['grade'] = grade['grade']
            return traditional_grade

    return calculation_dictionaries[-1]




