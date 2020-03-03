import itertools

from utilities.cbl_calculator import CUTOFF_DATE


def safe_round(num, digits):
    if num:
        return round(num, 2)
    else:
        return num


def make_outcome_avg_dicts(outcome_results, grades):
    outcome_averages = []

    for grade in grades:
        student_dict = {'user_name': grade.user.name, 'user_id': grade.user.id,
                        'grade': grade.grade, 'email': grade.user.login_id,
                        'course_id': grade.course_id}
        user_id = grade.user.id
        stu_aligns = list(filter(lambda student: student.user_id == user_id,
                                 outcome_results))
        for outcome_id, out_aligns in itertools.groupby(stu_aligns, lambda
                x: x.outcome_id):
            aligns = list(out_aligns)
            full_sum = sum([o.score for o in aligns])
            num_of_aligns = len(aligns)
            full_avg = full_sum / num_of_aligns
            temp_avg = {'avg': safe_round(full_avg, 2),
                        'outcome_id': outcome_id}

            filtered_align = [o.score for o in out_aligns if
                              o.submitted_or_assessed_at < CUTOFF_DATE]
            if len(filtered_align) > 0:
                min_score = min(filtered_align)
                drop_avg = (full_sum - min_score) / (num_of_aligns - 1)
                if drop_avg > full_avg:
                    temp_avg = {'avg': safe_round(drop_avg, 2),
                                'outcome_id': outcome_id}
            student_dict[str(outcome_id)] = temp_avg['avg']

        outcome_averages.append(student_dict)

    return outcome_averages


def format_users(users):
    keys = ['id', 'name']
    users = [dict(zip(keys, (user['id'], user['name']))) for user in users]
    return sorted(users, key=lambda x: x['name'])
