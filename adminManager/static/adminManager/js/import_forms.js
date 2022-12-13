
function addInputForm() {
    // simply loops hidden extra forms and reveals first one
    formDivs = document.querySelectorAll('.input-form-div');
    for (div of formDivs) {
        if (div.style.display == 'none') {
            div.style.display = '';
            return;
        }
    }
    // no more hidden forms
    // prompt user to save in order to continue adding
    alert('To continue adding more inputs, please save your work.')
}