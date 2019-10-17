from cbl_calculator import calculate_traditional_grade

# todo - add to db or as a json file
calculation_dictionaries = {
    'A': {
        'grade': 'A',
        'threshold': 3.5,
        'min_score': 3
    },
    'A-': {
        'grade': 'A-',
        'threshold': 3.5,
        'min_score': 2.5
    },
    'B+': {
        'grade': 'B+',
        'threshold': 3,
        'min_score': 2.5
    },
    'B': {
        'grade': 'B',
        'threshold': 3,
        'min_score': 2.25
    },
    'B-': {
        'grade': 'B-',
        'threshold': 3,
        'min_score': 2
    },
    'C': {
        'grade': 'C',
        'threshold': 2.5,
        'min_score': 2
    },
    'I': {
        'grade': 'I',
        'threshold': 0,
        'min_score': 0
    },
    'n/a': {
        'grade': 'n/a',
        'threshold': 'n/a',
        'min_score': 'n/a',
    }
}


def cmp_dict(d1, d2):
    if d1.keys() != d2.keys():
        return False

    for k, v in d1.items():
        if d1[k] != d2[k]:
            return False

    return True


# These probably shouldn't include the calculate_percentage function
def test_calculate_final_grade():
    # Test for an A

    test_a1 = 50 * [4.] + [3.]
    test_a2 = 8 * [3.5]
    assert calculate_traditional_grade(test_a1)['grade'] == 'A'
    assert calculate_traditional_grade(test_a2)['grade'] == 'A'

    # Test for A-
    test_a_minus1 = 50 * [4.] + [2.5]
    assert calculate_traditional_grade(test_a_minus1)['grade'] == 'A-'

    # # Test for B+
    assert cmp_dict(calculate_traditional_grade(8 * [3.]),
                    calculation_dictionaries['B+'])
    assert cmp_dict(calculate_traditional_grade(25 * [3.49] + [2.5]),
                    calculation_dictionaries['B+'])

    # # Test for B
    test_b1 = 24 * [4.] + [2.25]
    test_b2 = 24 * [3.49] + [2.25]
    assert cmp_dict(calculate_traditional_grade(test_b1),
                    calculation_dictionaries['B'])
    assert cmp_dict(calculate_traditional_grade(test_b2),
                    calculation_dictionaries['B'])

    # Test for B-
    test_b_minus1 = 24 * [4.] + [2.]
    test_b_minus2 = 24 * [3.49] + [2.]
    assert cmp_dict(calculate_traditional_grade(test_b_minus1),
                    calculation_dictionaries['B-'])
    assert cmp_dict(calculate_traditional_grade(test_b_minus2),
                    calculation_dictionaries['B-'])

    # Test for C
    test_c3 = 24 * [2.99] + [2.5]
    test_c4 = 24 * [2.99] + [2.]
    assert cmp_dict(calculate_traditional_grade(test_c3),
                    calculation_dictionaries['C'])
    assert cmp_dict(calculate_traditional_grade(test_c4),
                    calculation_dictionaries['C'])

    # Test for DV
    test_dv1 = 10 * [2.49]
    assert cmp_dict(calculate_traditional_grade(test_dv1),
                    calculation_dictionaries['I'])

    test_dv2 = 50 * [4.] + [1.99]
    assert cmp_dict(calculate_traditional_grade(test_dv2),
                    calculation_dictionaries['I'])

    # Test for n/a
    test_na1 = []
    assert cmp_dict(calculate_traditional_grade(test_na1),
                    calculation_dictionaries['n/a'])
    test_na2 = [-1]
    assert cmp_dict(calculate_traditional_grade(test_na1),
                    calculation_dictionaries['n/a'])
