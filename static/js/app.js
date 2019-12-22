function makeCourseTable(students) {
    let $table_el = $(`#courseTable`);
    var columns = [
        {
            field: 'user.name',
            title: 'Student',
            sortable: true
        },
        {
            field: 'grade',
            title: 'Grade',
            sortable: true,
            filterControl: 'select'
        },
        {
            field: 'threshold',
            title: 'Criteria 1',
            sortable: true
        },
        {
            field: 'min_score',
            title: 'Criteria 2',
            sortable: true
        }
    ];

    $table_el.bootstrapTable({
        columns: columns,
        data: students,
        height: 1200,
        search: true,
        filterControl: true,
        showSearchClearButton: true,
        detailView: true,
        onExpandRow: function (index, row, $detail) {
            let $new_table = $detail.html('<table></table>').find('table')
            let outcomes = row['outcomes'];
            makeOutcomesTable(outcomes, $new_table)
        }
    })
}

function makeMasteryTable(data) {
    // Get unique outcomes
    var $tableOut = $('#outcomesTable');

    const outcomes_list = [];
    outcomes_list.push({field: 'name', title:'Student Name', sortable: true});
    const student_outcomes = [];
    const map = new Map();
    for (const student of data) {
        let student_dict = {};
        student_dict['name'] = student.user.name;
        for (const outcome of student['outcomes']) {
            if (!map.has(outcome['outcome_id'])) {
                map.set(outcome['outcome_id'], true);    // set any value to Map
                outcomes_list.push({
                    field: outcome['outcome_id'],
                    title: outcome['title'],
                    sortable: true
                });
            }

            student_dict[outcome['outcome_id']] = outcome['outcome_avg'];

        }
        student_outcomes.push(student_dict);
    }


    $tableOut.bootstrapTable({
        columns: outcomes_list,
        data: student_outcomes,
        height: 1200,
        search: true,
        showColumns: true,
        showColumnsToggleAll: true,
        showSearchClearButton: true,
    });


}


function makeOutcomesTable(outcomes, $table_el) {
    // let $table_el = $(`#table-${idx + 1}`);
    // let $table_el = $el;

    console.log(outcomes);
    // Check for a display name and use if available
    outcomes.forEach(outcome => {
            if (outcome['display_name']) {
                outcome['title'] = outcome['display_name']
            }
        }
    );

    var columns = [
        {
            field: 'title',
            title: 'Outcome',
            sortable: true
        },
        {
            field: 'outcome_avg',
            title: 'Outcome Average',
            sortable: true
        },
    ];

    $table_el.bootstrapTable({
        columns: columns,
        data: outcomes,
        detailView: true,
        onExpandRow: function (index, row, $detail) {
            expandTable($detail, row)
        }

    });

}

function expandTable($el, outcome) {

    let alignments = outcome['alignments'];

    // buildSubTable($el.html('<table></table>').find('table'), alignments);
    let $subTable = $el.html('<table></table>').find('table')
    let columns = [
        {
            field: 'name',
            title: 'Assignment Name',
            sortable: true
        },
        {
            field: 'score',
            title: 'Score',
            sortable: true
        },
    ];
    $subTable.bootstrapTable({
        columns: columns,
        data: alignments,

    });


}

function buildSubTable($el, alignments) {
    let columns = [
        {
            field: 'name',
            title: 'Assignment Name',
            sortable: true
        },
        {
            field: 'score',
            title: 'Score',
            sortable: true
        },
    ];
    $el.bootstrapTable({
        columns: columns,
        data: alignments,

    });
}

$(function () {
    var $aButton = $('#A');
    $aButton.click(function () {
        $table.bootstrapTable('filterBy', {
            grade: 'B'
        })
    })
})