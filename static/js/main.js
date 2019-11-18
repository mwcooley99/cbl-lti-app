function showHide(elem) {
    var students = document.getElementsByClassName("student");
    for (var i = 0; i < students.length; i++) {
        students[i].style.display = 'none';
    }
    //unhide the selected div
    var sel = document.getElementById('sel').value;
    console.log("accordion" + sel);
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
        console.log("Hello");
        if (this.id == 'all') {
            $('.student-card').show();
        } else {
            console.log(this.id);
            var $el = $('.' + this.id).show();
            $('.student-card').not($el).hide();
        }
        $btns.removeClass('active');
        $(this).addClass('active');
    });
})