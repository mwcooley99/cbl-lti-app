import pandas as pd
import numpy as np
import json

import re
from datetime import datetime

import time

from utilities.cbl_calculator import calculate_traditional_grade, weighted_avg
from utilities.canvas_api import get_courses, get_outcome_results, \
    get_course_users_ids, create_outcome_dataframes, get_course_users

from utilities.db_functions import insert_grades_to_db, create_record, \
    update_users, delete_outcome_results, upsert_alignments, \
    upsert_outcome_results, upsert_outcomes, upsert_courses, \
    query_current_outcome_results, update_outcome_res_dropped, get_db_courses

OUTCOMES_TO_FILTER = (
    2269, 2270, 2923, 2922, 2732,
    2733)

CUTOFF_DATE = datetime(2020, 1, 1)


def make_grade_object(grade, outcome_avgs, record_id, course, user_id):
    '''
    Creates grade dictionary for grades table
    :param grade: Letter Grade
    :param outcome_avgs: List of outcome average info dictionaries
    :param record_id: Current Record ID
    :param course: Course Dictionary
    :param user_id: User ID
    :return: return dictionary formatted for Grades Table
    '''
    # store in a dict
    grade = dict(
        user_id=user_id,
        course_id=course['id'],
        grade=grade['grade'],
        threshold=grade['threshold'],
        min_score=grade['min_score'],
        record_id=record_id,
        outcomes=outcome_avgs
    )

    return grade


def outcome_results_to_df_dict(df):
    return df.to_dict('records')


def make_empty_grade(course, grades_list, record_id, user_id):
    '''
    Create empty grade for non-graded courses
    :param course: course dictionary
    :param grades_list: list to append empty grade to
    :param record_id: record ID
    :param user_id: user_id
    :return: 
    '''
    empty_grade = {'grade': 'n/a', 'threshold': None,
                   'min_score': None}
    grade = make_grade_object(empty_grade, [], record_id, course,
                              user_id)
    grades_list.append(grade)


def make_outcome_result(outcome_result, course_id, enrollment_term):
    temp_dict = {
        'id': outcome_result['id'],
        'score': outcome_result['score'],
        'course_id': course_id,
        'user_id': outcome_result['links']['user'],
        'outcome_id': outcome_result['links']['learning_outcome'],
        'alignment_id': outcome_result['links']['alignment'],
        'submitted_or_assessed_at': outcome_result['submitted_or_assessed_at'],
        'last_updated': datetime.utcnow(),
        'enrollment_term': enrollment_term

    }
    return temp_dict


def format_outcome(outcome):
    temp_dict = {
        'id': outcome['id'],
        'display_name': outcome['display_name'],
        'title': outcome['title'],
        'calculation_int': outcome['calculation_int']
    }

    return temp_dict


def format_alignments(alignment):
    ids = ['id', 'name']
    return {_id: alignment[_id] for _id in ids}


def pull_outcome_results(current_term=10):
    # get all courses for current term todo move outside of this function
    courses = get_courses(current_term)
    upsert_courses(courses)

    # get outcome result rollups for each course and list of outcomes
    pattern = '@dtech|Teacher Assistant|LAB Day|FIT|Innovation Diploma FIT'

    for idx, course in enumerate(courses):
        print(course['id'])
        print(f'{course["name"]} is course {idx + 1} our of {len(courses)}')

        # Check if it's a non-graded course
        if re.match(pattern, course['name']):
            print(course['name'])
            continue

        # get course users
        users = get_course_users(course)
        user_ids = [user['id'] for user in users]

        outcome_results, alignments, outcomes = get_outcome_results(course, user_ids=user_ids)

        # Format results, Removed Null filter (works better for upsert)
        outcome_results = [
            make_outcome_result(outcome_result, course['id'], current_term)
            for
            outcome_result in outcome_results]

        # Format outcomes
        outcomes = [format_outcome(outcome) for outcome in outcomes]
        # Filter out duplicate outcomes
        outcomes = [val for idx, val in enumerate(outcomes) if
                    val not in outcomes[idx + 1:]]

        # format Alignments
        alignments = [format_alignments(alignment) for alignment in alignments]
        # filter out duplicate alignments
        alignments = [val for idx, val in enumerate(alignments) if
                      val not in alignments[idx + 1:]]

        # If there are results to upload
        if outcome_results:
            print(f'deleting outcome_results for {course["name"]}')
            delete_outcome_results(course['id'])
            print(f'outcomes results to upload: {len(outcome_results)}')
            upsert_outcome_results(outcome_results)
            print('result upsert complete')
            upsert_outcomes(outcomes)
            print('outcome upsert complete')
            upsert_alignments(alignments)
            print('alignment upsert complete')


def insert_grades(current_term=10):
    print(f'Grade pull started at {datetime.now()}')
    outcome_results = query_current_outcome_results(current_term)

    # rank the outcomes
    rank_group_cols = ['links.user', 'course_id', 'outcome_id']
    outcome_results['drop_eligible_scores'] = outcome_results.where(
        outcome_results['submitted_or_assessed_at'] < CUTOFF_DATE)['score']

    outcome_results['rank'] = outcome_results.groupby(rank_group_cols)[
        'drop_eligible_scores'].rank('first')

    # Create outcomes df
    outcome_cols = ['outcome_id', 'title', 'display_name']
    outcomes = outcome_results[outcome_cols].drop_duplicates()

    unfiltered_avgs = calc_outcome_avgs(outcome_results)

    # add outcome metadata back in
    unfiltered_avgs = pd.merge(unfiltered_avgs, outcomes, how='left',
                               on='outcome_id')

    # Add column to alignments noting if it was dropped
    avg_merge_cols = ['links.user', 'course_id', 'outcome_id']
    outcome_results = pd.merge(outcome_results, unfiltered_avgs, how='left',
                               on=avg_merge_cols)
    outcome_results['dropped'] = np.where(
        (outcome_results['drop_min']) & (outcome_results['rank'] == 1.0), True,
        False)

    dropped_dict = outcome_results[['_id', 'dropped']].to_dict('records')
    update_outcome_res_dropped(dropped_dict)

    # Convert datetime to string for serializtion into dictionaries
    outcome_results['submitted_or_assessed_at'] = outcome_results[
        'submitted_or_assessed_at'].dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


    # make grades df
    group_cols = ['links.user', 'course_id']
    grades = unfiltered_avgs.groupby(group_cols).agg(
        {'outcome_avg': calculate_traditional_grade})
    grades.reset_index(inplace=True)


    # Break up grades into their own columns
    grades[['unfiltered_grades', 'unfiltered_idx']] = pd.DataFrame(
        grades['outcome_avg'].values.tolist(), index=grades.index)

    # todo - refactor. Not needed anymore
    grades['final_grade'] = grades['unfiltered_grades']

    # Break up grade dict into columns
    grades[['threshold', 'min_score', 'grade']] = pd.DataFrame(
        grades['final_grade'].values.tolist(), index=grades.index)

    # Make a new record
    print(f'Record created at {datetime.now()}')
    record_id = create_record(current_term)
    grades['record_id'] = record_id

    # Create grades_dict for database insert
    grades.rename(columns={'links.user': 'user_id'}, inplace=True)
    grade_cols = ['course_id', 'user_id', 'threshold', 'min_score', 'grade', 'record_id']
    grades_list = grades[grade_cols].to_dict('r')

    # Insert into Database
    if len(grades_list):
        insert_grades_to_db(grades_list)


def calc_outcome_avgs(outcome_results):
    '''
    Calculates outcome averages with both simple and weighted averages,
    choosing the higher of the two
    :param outcome_results:
    :return: DataFrame of outcome_averages with max of two averages
    '''

    group_cols = ['links.user', 'outcome_id', 'course_id']

    # Calculate the average without dropping the low score
    no_drop_avg = outcome_results.groupby(group_cols).agg(
        no_drop_score=('score', 'mean')).reset_index()

    # Calculate the average without dropping the low score
    outcome_results_drop_min = outcome_results[outcome_results['rank'] != 1.0]
    drop_avg = outcome_results_drop_min.groupby(
        group_cols).agg(drop_score=('score', 'mean')).reset_index()

    # Merge them together
    outcome_averages = pd.merge(no_drop_avg, drop_avg, on=group_cols)

    # Pick the greater average and note if a score was dropped
    outcome_averages['outcome_avg'] = outcome_averages[
        ['no_drop_score', 'drop_score']].max(axis=1).round(2)
    outcome_averages['drop_min'] = np.where(
        outcome_averages['no_drop_score'] < outcome_averages['drop_score'],
        True, False)

    return outcome_averages


def add_outcome_meta(outcome_results, outcomes, alignments):
    '''
    Adds outcome and assignment alignment data to the results dataframe
    :param outcome_results: DataFrame
    :param outcomes: DataFrame
    :param alignments: DataFrame
    :return: DataFrame with outcome and assignments data
    '''
    outcome_results = pd.merge(outcome_results, outcomes, how='left',
                               on='outcome_id')
    outcome_results = pd.merge(outcome_results, alignments[['id', 'name']],
                               how='left', left_on='links.alignment',
                               right_on='id')
    outcome_results['score_int'] = list(
        zip(outcome_results['score'],
            outcome_results['calculation_int'],
            outcome_results['outcome_id']))
    return outcome_results


def format_outcomes(outcomes):
    '''
    Cleans up formatting of outcomes DataFrame
    :param outcomes: outcomes DataFrame
    :return: Reformatted outcomes DataFrame
    '''
    outcomes['id'] = outcomes['id'].astype('int')
    outcomes = outcomes.rename(columns={'id': 'outcome_id'})
    return outcomes


def format_outcome_results(outcome_results):
    '''
    Cleans up formatting of outcome_results DataFrame
    :param outcome_results: outcome_results DataFrame
    :return: Reformatted outcomes DataFrame
    '''
    new_col_names = {'links.learning_outcome': 'outcome_id'}
    outcome_results = outcome_results.rename(columns=new_col_names)
    outcome_results['outcome_id'] = outcome_results[
        'outcome_id'].astype('int')
    outcome_results = outcome_results.sort_values(['links.user', 'outcome_id',
                                                   'submitted_or_assessed_at'])

    return outcome_results


def update_course_students(current_term):
    # Query current courses
    courses = get_db_courses(current_term)
    for course in courses:
        print(course)


    # for course in courses
        # Get course students
        # Get user IDs in a list
        # delete previous course roster
        # insert current roster

    pass


def update_courses(current_term):
    courses = get_courses(current_term)
    upsert_courses(courses)



if __name__ == '__main__':
    start = time.time()
    current_term = 11
    # update_users()
    update_course_students(current_term)
    # update_courses(current_term)
    # update_course_students(current_term)
    # pull_outcome_results(current_term=11)
    # insert_grades(current_term=11)
    # delete_outcome_results(345)

    end = time.time()
    print(f'pull took: {end - start} seconds')
