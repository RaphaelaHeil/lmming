function changeCreateExtractionButtonVisibility(visible){
    // grab reference and show/hide
    // id="create_extraction_button"
}

function changeSettingsButtonVisibility(visible){
    // grab reference and show/hide
    // id="settings_button"
}

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





