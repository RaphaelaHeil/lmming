$(document).ready(function () {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })

});


function checkboxChange() {
    enabled = false

    for (checkbox of $(".checkable")) {
        if ($(checkbox).prop('checked')) {
            enabled = true;
            break;
        }
    }

    var i = $(".checkbox-action-button")
    if (enabled) {
        for (element of i) {
            $(element).removeClass('disabled');
        }
    } else {
        for (element of i) {
            $(element).addClass('disabled');
        }
        $("#checkAll").prop('checked', false);
    }
};

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