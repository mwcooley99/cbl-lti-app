import json
import math
from datetime import datetime

import pandas as pd

from utilities.db_functions import get_calculation_dictionaries


def weighted_avg(scores):
    s = scores.apply(pd.Series)
    if len(s) == 1:
        return s.iloc[0, 0]

    # need check that there's more than 1 outcome alignment
    first_weight = (100 - s.iloc[0, 1]) / 100
    final_weight = s.iloc[0, 1] / 100
    w_avg = first_weight * s.iloc[:-1, 0].mean() + final_weight * s.iloc[-1, 0]
    return w_avg


def outcome_avg(alignments=None):
    pass


def calculate_traditional_grade(scores, calculation_dictionaries):
    # check if the outcome is assessed.
    scores = scores.to_list()
    # print(scores)
    if len(scores) == 0 or scores[0] == -1:
        return {
            "grade": "n/a",
            "threshold": None,
            "min_score": None,
        }

    scores_sorted = sorted(scores, reverse=True)

    # Find the 75% threshold --> floored
    threshold_index = math.floor(0.75 * len(scores_sorted)) - 1

    # Calculate the threshold scores to generate grade
    threshold_score = scores_sorted[threshold_index]
    min_score = scores_sorted[-1]
    traditional_grade = dict(threshold=threshold_score, min_score=min_score)

    for _i in range(len(calculation_dictionaries)):
        grade = calculation_dictionaries[_i]
        if threshold_score >= grade["threshold"] and min_score >= grade["min_score"]:
            traditional_grade["grade"] = grade["grade"]
            return traditional_grade

    return calculation_dictionaries[-1]


if __name__ == "__main__":
    with open("../out/alignments.json", "r") as fp:
        alignments = json.load(fp)

    # courses = []
    # for course_id, alignments in itertools.groupby(alignments, lambda t: t['course_id']):
    #     for
