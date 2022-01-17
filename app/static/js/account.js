function makeIncompleteTable(incompletes, table){
    incompletes.map((value, index) => {
        console.log(value);
        let name = value.name.trim().split(/\s+/);
        value.name = name.pop() + ', ' + name.join(' ');
        return value;
      });

    incompletes.sort((a, b) => {
        let fa = a.name.toLowerCase();
        let fb = b.name.toLowerCase();
        if (fa < fb) {
          return -1;
        }
        if (fa > fb) {
          return 1;
        }
        return 0;
      });
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
            filterControl: 'select',
            sortable: true
        },
    ];

    table.bootstrapTable({
        columns: columns,
        data: incompletes,
        search: true,
        pagination: true,
        filterControl: true,
        showSearchClearButton: true,
        showExport: true,
        exportTypes: ['csv'],
    })
}
