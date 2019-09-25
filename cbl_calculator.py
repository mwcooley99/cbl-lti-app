from operator import itemgetter
import json

from canvasapi import Canvas
import settings

def get_min_score(scores):
    '''
    Find the lowest value in list of dictionaries
    :param scores: list of dictionaries
    :return: tuple ('outcome_id', min_score)
    '''

    # Check if list is empty
    if len(scores) == 0:
        return ('empty', 0) # todo - should be something besides empty
    print(scores)
    return sorted(scores, key=itemgetter(1))[0]


def count_above_number(scores, number):
    '''

    :param scores: List of tuples (outcome, score)
    :param number: Number to check if score is higher than
    :return: count of scores >= number
    '''
    return len([score for score in scores if score[1] >= number])


def calculate_percentage_per_threshold(scores, thresholds=(3.5, 3.0, 2.5, 0)):
    num_of_scores = len(scores)

    # Edge case of zero scores
    if num_of_scores == 0:
        return dict(zip(thresholds, 4 * [0]))

    percents = {
        threshold: round(count_above_number(scores, threshold) / num_of_scores,
                         2)
        for threshold in thresholds}

    return percents


def extract_scores_from_outcome_rollup(rollup):
    '''
    Get scores and outcomes from rollup
    :param rollup:
    :return: tuple ('outcome_id', score)
    '''

    scores = [(outcome['links']['outcome'], outcome['score']) for outcome in
              rollup['scores']]
    return scores


def calculate_final_grade(percents, min_score, scores):
    '''
    Calculate the traditional grade from the outcome scores and thresholds
    :param scores: list of outcome scores
    :param thresholds: list in desc order of the grade level threshold
    :return: Traditional Grade
    '''

    # check if the outcome is assessed.
    if len(scores) == 0:
        return {
            'grade': 'n/a',
            'threshold': 'n/a',
            'min_score': 'n/a',
        }

    # TODO - This should probably wind up in the database
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

    for grade in calculation_dictionaries:
        if percents[grade['threshold']] >= 0.75 and min_score >= grade[
            'min_score']:
            return grade

    return calculation_dictionaries[-1]


def rollup_to_traditional_grade(rollup, thresholds=(3.5, 3.0, 2.5, 0)):
    scores = extract_scores_from_outcome_rollup(rollup) # todo - remove this
    min_score = get_min_score(scores)
    percents = calculate_percentage_per_threshold(scores,
                                                  thresholds)

    traditional_grade = calculate_final_grade(percents, min_score[1], scores)

    # TODO - remove redundant information
    # traditional_grade_rollup = {
    #     'min_score': min_score,
    #     'percents': percents,
    #     'traditional_grade': traditional_grade
    # }

    return traditional_grade


if __name__ == '__main__':
    canvas = Canvas(settings.CANVAS_API_URL, settings.CANVAS_API_KEY)
    user = canvas.get_user(466)
    courses = user.get_courses(enrollment_type='student', enrollment_term=10)
    pattern = '^@dtech|Innovation Diploma FIT'


    # traditional_grade_rollup = rollup_to_traditional_grade({
    #     "scores": [
    #         {
    #             "score": 4.0,
    #             "title": "Unit 1 mid unit Exam",
    #             "submitted_at": "2019-09-01T00:29:00Z",
    #             "count": 1,
    #             "hide_points": False,
    #             "links": {
    #                 "outcome": "2864"
    #             }
    #         },
    #         {
    #             "score": 3.0,
    #             "title": "Unit 1 mid unit Exam",
    #             "submitted_at": "2019-09-01T00:29:00Z",
    #             "count": 1,
    #             "hide_points": False,
    #             "links": {
    #                 "outcome": "2866"
    #             }
    #         },
    #         {
    #             "score": 4.0,
    #             "title": "Unit 1 mid unit Exam",
    #             "submitted_at": "2019-09-01T00:29:00Z",
    #             "count": 1,
    #             "hide_points": False,
    #             "links": {
    #                 "outcome": "2868"
    #             }
    #         },
    #         {
    #             "score": 4.0,
    #             "title": "Exit Slip 1.1.2",
    #             "submitted_at": "2019-08-23T18:03:59Z",
    #             "count": 1,
    #             "hide_points": False,
    #             "links": {
    #                 "outcome": "2869"
    #             }
    #         },
    #         {
    #             "score": 4.0,
    #             "title": "Unit 1 mid unit Exam",
    #             "submitted_at": "2019-09-01T00:29:00Z",
    #             "count": 3,
    #             "hide_points": False,
    #             "links": {
    #                 "outcome": "2871"
    #             }
    #         }
    #     ],
    #     "links": {
    #         "user": "938",
    #         "section": "550",
    #         "course": 359
    #     }
    # })
    #
    # print(json.dumps(traditional_grade_rollup, indent=4))
