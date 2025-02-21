function allowRefresh() {
    var i = $("#tablediv .form-check-input");

    for (element of i) {
        if (element.checked) {
            return false
        }
    }
    return true
}

function toggleCheckboxes() {
    $(".checkable").prop('checked', $("#checkAll").prop('checked')).trigger("change");
}
