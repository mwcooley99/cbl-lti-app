function makeCourseTable(students, alignments) {
    let $table_el = $(`#courseTable`);

    var columns = [
        {
            field: 'user.name',
            title: 'Student',
            class: "headcol",
            sortable: true,

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
        height: 600,
        search: true,
        filterControl: true,
        showSearchClearButton: true,
        detailView: true,
        showExport: true,
        exportTypes: ['csv'],
        onExpandRow: function (index, row, $detail) {
            let $new_table = $detail.html('<table></table>').find('table');
            let outcomes = alignments.filter(a => a.user_id === row.user.id);
            makeOutcomesTablev2(outcomes, $new_table)
        }
    })
}

function makeMasteryTable(grades, alignments, outcomes) {
    // Get unique outcomes
    var $tableOut = $('#outcomesTable');

    // Create the columns for the table
    const columns = outcomes.map(function (value, index) {
        let temp_dict = {
            field: value['id'],
            title: value['title'],
            sortable: true,
        };
        return temp_dict;
    });

    // Add in User Name
    columns.unshift({
        field: 'user_name',
        title: 'Student Name',
        sortable: true,
        width: 90,
        widthUnit: "px"
    });


    const students = groupBy(alignments, 'user_id');

    const student_outcomes = [];
    for (const student of grades) {
        let student_dict = {};
        student_dict['user_name'] = student.user.name;
        student_dict['user_id'] = student.user.id;
        student_dict['grade'] = student.grade;
        let outcome_avgs = groupBy(students[student.user.id], o => o.outcome.id);
        for (const outcome of Object.keys(outcome_avgs)) {
            let alignments = outcome_avgs[outcome];
            let filtered_align = alignments.filter(a => !a.dropped);
            let avg = filtered_align.reduce((a, {score}) => a + score, 0) / filtered_align.length;
            student_dict[outcome] = avg.toFixed(2);
        }
        student_outcomes.push(student_dict);

    }


    $tableOut.bootstrapTable({
        columns: columns,
        data: student_outcomes,
        height: 600,
        search: true,
        showColumns: true,
        showColumnsToggleAll: true,
        showSearchClearButton: true,
        showExport: true,
        exportTypes: ['csv'],
        fixedColumns: true,

    });


}


function makeOutcomesTable(outcomes, $table_el) {
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
        // height: 480,
        detailView: true,
        onExpandRow: function (index, row, $detail) {

            expandTable($detail, row)
        }

    });

}

function makeOutcomesTablev2(alignments, $table_el) {
    // Check for a display name and use if available
    var outcomes = groupBy(alignments, a => a.outcome.id);


    var outcome_avgs = Object.keys(outcomes).map(function (key) {
        let outcome = {};
        let alignments = outcomes[key];
        let filtered_align = alignments.filter(a => !a.dropped);
        outcome['outcome_avg'] = filtered_align.reduce((a, {score}) => a + score, 0) / filtered_align.length;
        outcome['outcome_avg'] = outcome['outcome_avg'].toFixed(2);
        let outcome_detail = alignments[0]['outcome'];
        outcome['title'] = outcome_detail['display_name'] ? outcome_detail['display_name'] : outcome_detail['title'];
        outcome['alignments'] = alignments;

        return outcome;
    });



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
        data: outcome_avgs,
        // height: 480,
        detailView: true,
        onExpandRow: function (index, row, $detail) {

            expandTablev2($detail, row)
        }

    });

}

function expandTablev2($el, outcome) {
    let alignments = outcome['alignments'];

    let $card = $el.html("<div class='card p-3'></div>").find('.card');
    let text = "";
    let drop_min = alignments.filter(a => a.dropped).length;

    if (drop_min > 0) {
        text = "<p>The lowest score <b>was</b> dropped from this outcome because it helped your average.</p>"
    } else {
        text = "<p>The lowest score <b>was not</b> dropped from this outcome because dropping it would not have helped your average.</p>"
    }

    let $details = $card.append(text);
    let $subTable = $card.append('<table></table>').find('table');


    let columns = [
        {
            field: 'alignment.name',
            title: 'Assignment Name',
            sortable: true
        },
        {
            field: 'score',
            title: 'Score',
            align: 'center',
            sortable: true
        },
        {
            field: 'dropped',
            title: 'Dropped',
            align: 'center',
            formatter: function (value, row) {
                let icon = value ? "fas fa-circle" : "";
                return `<i class="${icon}"</i>`
            }
        },
        {
            field: 'submitted_or_assessed_at',
            title: 'Date Assessed',
            sortable: true,
            formatter: function(value, row) {
                let dt = new Date(`${value}Z`);
                return dt.toLocaleDateString();
            }
        }
    ];
    $subTable.bootstrapTable({
        columns: columns,
        data: alignments,
        // height:400

    });


}

function expandTable($el, outcome) {
    let alignments = outcome['alignments'];

    let $card = $el.html("<div class='card p-3'></div>").find('.card');
    let text = "";
    if (outcome['drop_min']) {
        text = "<p>The lowest score <b>was</b> dropped from this outcome because it helped your average.</p>"
    } else {
        text = "<p>The lowest score <b>was not</b> dropped from this outcome because would not have helped your average.</p>"
    }

    let $details = $card.append(text);
    let $subTable = $card.append('<table></table>').find('table');


    let columns = [
        {
            field: 'name',
            title: 'Assignment Name',
            sortable: true
        },
        {
            field: 'score',
            title: 'Score',
            align: 'center',
            sortable: true
        },
        {
            field: 'dropped',
            title: 'Dropped',
            align: 'center',
            formatter: function (value, row) {
                let icon = value ? "fas fa-circle" : "";
                return `<i class="${icon}"</i>`
            }
        }
    ];
    $subTable.bootstrapTable({
        columns: columns,
        data: alignments,
        // height:400

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
    $button2.click(function () {
        $courseTable.bootstrapTable('collapseAllRows')
    })
});

function mcellStyle(value, row, index) {
    var classes = [
        'bg-blue',
        'bg-green',
        'bg-orange',
        'bg-yellow',
        'bg-red'
    ];

    if (index % 2 === 0 && index / 2 < classes.length) {
        return {
            classes: classes[index / 2]
        }
    }
    return {
        css: {
            color: 'blue'
        }
    }
}