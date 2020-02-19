import itertools

def safe_round(num, digits):
    if num:
        return round(num, 2)
    else:
        return num


def make_outcome_avg_dicts(outcome_results):
    outcome_averages = []
    for student_id, stu_aligns in itertools.groupby(outcome_results,
                                                    lambda t: t.user_id):
        temp_dict = {'user_id': student_id, 'outcome_avgs': []}
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
            temp_dict['outcome_avgs'].append(temp_avg)
        outcome_averages.append(temp_dict)
    return outcome_averages


def format_users(users):
    keys = ['id', 'name']
    users = [dict(zip(keys, (user['id'], user['name']))) for user in users]
    return sorted(users, key=lambda x: x['name'])
