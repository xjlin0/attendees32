Attendees.directoryPrintConfiguration = {

  init: () => {
    console.log('static/js/persons/directory_print_configuration_view.js');
    Attendees.directoryPrintConfiguration.catchSubmitToGeneratePDF();
  },

  catchSubmitToGeneratePDF: () => {
    const configurationForm = document.getElementById("directory-print-configuration");
    configurationForm.addEventListener("submit", (event) => {

      event.preventDefault();


      const formData = new FormData(event.target);
      const formProps = Object.fromEntries(formData);
      console.log('clicked! here is formProps');
      console.log(formProps);
      //document.directoryPrintConfiguration['directory-header'].value;
    });
  },

};

$(document).ready(() => {
  Attendees.directoryPrintConfiguration.init();
});
