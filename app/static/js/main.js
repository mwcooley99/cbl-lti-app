function showHide(elem) {
    var students = document.getElementsByClassName("student");
    for (var i = 0; i < students.length; i++) {
        students[i].style.display = 'none';
    }
    //unhide the selected div
    var sel = document.getElementById('sel').value;
    document.getElementById("accordion" + sel).style.display = 'block';
}

$(document).ready(function () {
    $("#myInput").on("keyup", function () {
        var value = $(this).val().toLowerCase();
        $(".student-name").filter(function () {
            $(this).closest(".card").toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });
});

$(document).ready(function () {
    var $btns = $('.btn').click(function () {
        if (this.id == 'all') {
            $('.student-card').show();
        } else {
            var $el = $('.' + this.id).show();
            $('.student-card').not($el).hide();
        }
        $btns.removeClass('active');
        $(this).addClass('active');
    });
});

var groupBy = function (arr, criteria) {


    return arr.reduce(function (obj, item) {

        // Check if the criteria is a function to run on the item or a property of it
        var key = typeof criteria === 'function' ? criteria(item) : item[criteria];

        // If the key doesn't exist yet, create it
        if (!obj.hasOwnProperty(key)) {
            obj[key] = [];
        }

        // Push the value to the object
        obj[key].push(item);

        // Return the object to the next item in the loop
        return obj;

    }, {});
};
