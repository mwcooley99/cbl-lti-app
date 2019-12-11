import math

calculation_dictionaries = [
    {
        'grade': 'A',
        'threshold': 3.3,
        'min_score': 3
    },
    {
        'grade': 'A-',
        'threshold': 3.3,
        'min_score': 2.5
    },
    {
        'grade': 'B+',
        'threshold': 2.6,
        'min_score': 2.5
    },
    {
        'grade': 'B',
        'threshold': 2.6,
        'min_score': 0
    },
    {
        'grade': 'B-',
        'threshold': 2.6,
        'min_score': 0
    },
    {
        'grade': 'C',
        'threshold': 2.2,
        'min_score': 0
    },
    {
        'grade': 'I',
        'threshold': 0,
        'min_score': 0
    }
]


def calculate_traditional_grade(scores):
    # check if the outcome is assessed.
    if len(scores) == 0 or scores[0] == -1:
        return {
            'grade': 'n/a',
            'threshold': None,
            'min_score': None,
        }, 0

    scores_sorted = sorted(scores, reverse=True)

    # Find the 75% threshold --> floored
    threshold_index = math.floor(0.75 * len(scores_sorted)) - 1

    # Calculate the threshold scores to generate grade
    threshold_score = scores_sorted[threshold_index]
    min_score = scores_sorted[-1]
    traditional_grade = dict(
        threshold=threshold_score,
        min_score=min_score
    )

    for _i in range(len(calculation_dictionaries)):
        grade = calculation_dictionaries[_i]
        if threshold_score >= grade['threshold'] and min_score >= grade[
            'min_score']:
            traditional_grade['grade'] = grade['grade']
            return traditional_grade, _i

    return calculation_dictionaries[-1]
