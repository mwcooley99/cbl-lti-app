function showHide(elem) {
    var students = document.getElementsByClassName("student");
    for (var i = 0; i < students.length; i++) {
        students[i].style.display = 'none';
    }
    //unhide the selected div
    var sel = document.getElementById('sel').value;
    console.log("accordion"+sel);
    document.getElementById("accordion"+sel).style.display = 'block';
}

