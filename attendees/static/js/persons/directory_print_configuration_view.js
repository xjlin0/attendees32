Attendees.directoryPrintConfiguration = {

  init: () => {
    console.log('static/js/persons/directory_print_configuration_view.js');
    Attendees.directoryPrintConfiguration.listenToFormSubmit();
  },

  listenToFormSubmit: () => {
    document.directoryPrintConfiguration.addEventListener('submit', Attendees.directoryPrintConfiguration.handleSubmitToGeneratePDF);
  },

  handleSubmitToGeneratePDF: (event) => {
    event.preventDefault();

    if (confirm('Do you want to see the directory for print? (This will take 2 minutes.)')) {
      const formData = new FormData(event.target);
      const searchParams = new URLSearchParams(formData);  // encodeURI break UTF8?
      location.href = `${document.directoryPrintConfiguration.action}?${searchParams}`;
    }
  },
};

$(document).ready(() => {
  Attendees.directoryPrintConfiguration.init();
});
