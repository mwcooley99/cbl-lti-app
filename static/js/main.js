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

var $btns = $('.btn').click(function () {
    if (this.id == 'all') {
        $('#parent > div').fadeIn(450);
    } else {
        var $el = $('.' + this.id).fadeIn(450);
        $('#parent > div').not($el).hide();
    }
    $btns.removeClass('active');
    $(this).addClass('active');
})