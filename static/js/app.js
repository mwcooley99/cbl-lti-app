function makeCourseTable(students) {
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
        height: 800,
        search: true,
        filterControl: true,
        showSearchClearButton: true,
        detailView: true,
        showExport: true,
        exportTypes: ['csv'],
        onExpandRow: function (index, row, $detail) {
            let $new_table = $detail.html('<table></table>').find('table');
            let outcomes = row['outcomes'];
            makeOutcomesTable(outcomes, $new_table)
        }
    })
}

function makeMasteryTable(data) {
    // Get unique outcomes
    var $tableOut = $('#outcomesTable');

    const outcomes_list = [];
    outcomes_list.push({
        field: 'name',
        title: 'Student Name',
        sortable: true,
        width: 900,
        widthUnit: "px"
    });
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
                    sortable: true,
                    class: 'result_table_col'
                });
            }

            student_dict[outcome['outcome_id']] = outcome['outcome_avg'];

        }
        student_outcomes.push(student_dict);
    }


    $tableOut.bootstrapTable({
        columns: outcomes_list,
        data: student_outcomes,
        height: 800,
        search: true,
        showColumns: true,
        showColumnsToggleAll: true,
        showSearchClearButton: true,
        showExport: true,
        exportTypes: ['csv'],
        fixedColumns: true
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
        // {
        //     field: 'drop_min',
        //     title: 'Drop Low Score',
        //     formatter: function (value, row) {
        //         let icon = value ? "far fa-check-circle": "far fa-times-circle"
        //         return `<i class="${icon}"</i>`
        //     }
        //
        // }
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
    console.log('**********');
    console.log(outcome_avgs);


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
        // {
        //     field: 'drop_min',
        //     title: 'Drop Low Score',
        //     formatter: function (value, row) {
        //         let icon = value ? "far fa-check-circle": "far fa-times-circle"
        //         return `<i class="${icon}"</i>`
        //     }
        //
        // }
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
    // alignments.forEach(function (alignment) {
    //     alignment['name'] = alignment.alignment.name;
    // });
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