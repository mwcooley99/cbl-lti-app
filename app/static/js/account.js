function makeIncompleteTable(incompletes, table){
    let columns = [
        {
            field: 'name',
            title: 'Student',
            class: "headcol",
            sortable: true,
            formatter: function (value, row) {
                let link = `<a href="student_dashboard/${row.user_id}">${value}</a>`;
                return link;
            }
        },
        {
            field: 'email',
            title: 'Email',
            sortable: true,
        },
        {
            field: 'incomplete_count',
            title: 'Incomplete Count',
            sortable: true
        },
    ];

    table.bootstrapTable({
        columns: columns,
        data: incompletes,
        search: true,
        pagination: true,
        showSearchClearButton: true,
        showExport: true,
        exportTypes: ['csv'],
    })
}
