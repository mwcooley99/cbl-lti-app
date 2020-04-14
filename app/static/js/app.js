function makeCourseTable(students, alignments) {
  let $table_el = $(`#courseTable`);
  var columns = [
    {
      field: "user.name",
      title: "Student",
      class: "headcol",
      sortable: true,
      formatter: function (value, row) {
        let link = `<a href="${row.course_id}/user/${row.user.id}">${value}</a>`;
        return link;
      },
    },
    {
      field: "grade",
      title: "Grade",
      sortable: true,
      filterControl: "select",
    },
    {
      field: "threshold",
      title: "Criteria 1",
      sortable: true,
    },
    {
      field: "min_score",
      title: "Criteria 2",
      sortable: true,
    },
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
    exportTypes: ["csv"],
    onExpandRow: function (index, row, $detail) {
      let $new_table = $detail.html("<table></table>").find("table");
      let outcomes = alignments.filter((a) => a.user_id === row.user.id);
      makeOutcomesTablev2(outcomes, $new_table);
    },
  });
}

function makeMasteryTable(grades, outcomes, masteryTable) {
  // Create the columns for the table
  const columns = outcomes.map(function (value, index) {
    let temp_dict = {
      field: value["id"],
      title: value["title"],
      sortable: true,
      // width: 100,
    };
    return temp_dict;
  });

  // Add in User Name
  columns.unshift(
    {
      field: "user_name",
      title: "Student Name",
      sortable: true,
      width: 90,
      widthUnit: "px",
      formatter: function (value, row) {
        let link = `<a href="${row.course_id}/user/${row.user_id}">${value}</a>`;
        return link;
      },
    },
    {
      field: "grade",
      title: "Grade",
      sortable: true,
      // width: 90,
      // widthUnit: "px",
      filterControl: "select",
    },
    {
      field: "email",
      title: "Email",
      // sortable: true,
      // width: 90,
      // widthUnit: "px"
    }
  );

  masteryTable.bootstrapTable({
    columns: columns,
    data: grades,
    // height: 600,
    search: true,
    showColumns: true,
    showColumnsToggleAll: true,
    filterControl: true,
    showSearchClearButton: true,
    showExport: true,
    exportTypes: ["csv"],
    fixedColumns: true,
    pagination: true,
    // stickyHeader: true
  });
}

function calcOutcomeAvg(alignments, drop_date, outcome) {
  let align_sum = alignments.reduce((a, { score }) => a + score, 0);
  let outcome_avg = align_sum / alignments.length;
  let dropped = false;

  // calculate drop average
  let filtered_align = alignments.filter(
    (a) => a.submitted_or_assessed_at <= drop_date
  );

  // If there's more than one alignment after the filter, check to see if dropping lowest score will help
  if (filtered_align.length > 0) {
    // Only check the filtered alignments for a min_score
    let min_score = filtered_align.reduce(
      (min, val) => (val.score < min ? val.score : min),
      filtered_align[0].score
    );
    let drop_avg = (align_sum - min_score) / (alignments.length - 1);
    // Check if average with low score dropped is better
    if (drop_avg > outcome_avg) {
      outcome_avg = drop_avg;
      dropped = true;
    }
  }
  return { outcome_avg, dropped };
}

function makeOutcomesTablev2(alignments, $table_el, drop_date) {
  // Check for a display name and use if available
  var outcomes = groupBy(alignments, (a) => a.outcome.id);

  // Calculate outcome averages, looping through the different outcome keys
  var outcome_avgs = Object.keys(outcomes).map(function (key) {
    let outcome = {};
    let alignments = outcomes[key];
    let outcome_detail = alignments[0]["outcome"];

    // calculate full average
    let { outcome_avg, dropped } = calcOutcomeAvg(
      alignments,
      drop_date,
      outcome
    );

    // Format the outcome information
    outcome["outcome_avg"] = outcome_avg.toFixed(2);
    outcome["dropped"] = dropped;
    outcome["title"] = outcome_detail["display_name"]
      ? outcome_detail["display_name"]
      : outcome_detail["title"];
    outcome["alignments"] = alignments;

    return outcome;
  });

  // Sort by outcome average
  outcome_avgs = outcome_avgs.sort((a, b) =>
    a.outcome_avg < b.outcome_avg ? 1 : -1
  );

  var columns = [
    {
      field: "title",
      title: "Outcome",
      sortable: true,
    },
    {
      field: "outcome_avg",
      title: "Outcome Average",
      sortable: true,
    },
  ];

  $table_el.bootstrapTable({
    columns: columns,
    data: outcome_avgs,
    // height: 480,
    detailView: true,
    onExpandRow: function (index, row, $detail) {
      expandTablev2($detail, row);
    },
  });
}

function expandTablev2($el, outcome) {
  let alignments = outcome["alignments"].sort((a, b) =>
    a.submitted_or_assessed_at < b.submitted_or_assessed_at ? 1 : -1
  );

  let $card = $el.html("<div class='card p-3'></div>").find(".card");
  let text = "";

  if (outcome["dropped"]) {
    text =
      "<p>The lowest score <b>was</b> dropped from this outcome because it helped your average.</p>";
  } else {
    text =
      "<p>The lowest score <b>was not</b> dropped from this outcome because dropping it would not have helped your average <b>OR</b> it was past the DROP DATE.</p>";
  }

  let $details = $card.append(text);
  let $subTable = $card.append("<table></table>").find("table");

  let columns = [
    {
      field: "alignment.name",
      title: "Assignment Name",
      sortable: true,
    },
    {
      field: "score",
      title: "Score",
      align: "center",
      sortable: true,
    },
    {
      field: "submitted_or_assessed_at",
      title: "Date Assessed",
      sortable: true,
      formatter: function (value, row) {
        let dt = new Date(`${value}Z`);
        return dt.toLocaleDateString();
      },
    },
  ];
  $subTable.bootstrapTable({
    columns: columns,
    data: alignments,
  });
}

//
// function expandTable($el, outcome) {
//     let alignments = outcome['alignments'];
//
//     let $card = $el.html("<div class='card p-3'></div>").find('.card');
//     let text = "";
//     if (outcome['drop_min']) {
//         text = "<p>The lowest score <b>was</b> dropped from this outcome because it helped your average.</p>"
//     } else {
//         text = "<p>The lowest score <b>was not</b> dropped from this outcome because would not have helped your average.</p>"
//     }
//
//     let $details = $card.append(text);
//     let $subTable = $card.append('<table></table>').find('table');
//
//
//     let columns = [
//         {
//             field: 'name',
//             title: 'Assignment Name',
//             sortable: true
//         },
//         {
//             field: 'score',
//             title: 'Score',
//             align: 'center',
//             sortable: true
//         },
//         {
//             field: 'dropped',
//             title: 'Dropped',
//             align: 'center',
//             formatter: function (value, row) {
//                 let icon = value ? "fas fa-circle" : "";
//                 return `<i class="${icon}"</i>`
//             }
//         }
//     ];
//     $subTable.bootstrapTable({
//         columns: columns,
//         data: alignments,
//         // height:400
//
//     });
//

// }

// function buildSubTable($el, alignments) {
//     let columns = [
//         {
//             field: 'name',
//             title: 'Assignment Name',
//             sortable: true
//         },
//         {
//             field: 'score',
//             title: 'Score',
//             sortable: true
//         },
//     ];
//     $el.bootstrapTable({
//         columns: columns,
//         data: alignments,
//
//     });
// }

// $(function () {
//     $button2.click(function () {
//         $courseTable.bootstrapTable('collapseAllRows')
//     })
// });

function mcellStyle(value, row, index) {
  var classes = ["bg-blue", "bg-green", "bg-orange", "bg-yellow", "bg-red"];

  if (index % 2 === 0 && index / 2 < classes.length) {
    return {
      classes: classes[index / 2],
    };
  }
  return {
    css: {
      color: "blue",
    },
  };
}
