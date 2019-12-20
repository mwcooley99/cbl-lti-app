function makeTable(outcomes, idx) {
            let $table_el = $(`#table-${idx + 1}`);

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
                onExpandRow: function(index, row, $detail) {
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