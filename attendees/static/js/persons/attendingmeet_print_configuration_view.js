Attendees.attendingmeetPrintConfiguration = {

  init: () => {
    console.log('static/js/persons/attendingmeet_print_configuration_view.js');
    Attendees.attendingmeetPrintConfiguration.prepareForm();
  },

  prepareForm: () => {
    Attendees.attendingmeetPrintConfiguration.attrs = document.querySelector('form#attendingmeet-print-configuration');
    document.attendingmeetPrintConfiguration.addEventListener('submit', Attendees.attendingmeetPrintConfiguration.handleSubmitToGeneratePDF);
  },

  handleSubmitToGeneratePDF: (event) => {
    event.preventDefault();
    alert("Submitted");
//    if (confirm('Do you want to see the directory for print? (This will take 2 minutes.)')) {
//      const formData = new FormData(event.target);
//      const searchParams = new URLSearchParams(formData);  // encodeURI break UTF8?
//      location.href = `${document.attendingmeetPrintConfiguration.action}?${searchParams}`;
//    }
  },
};

$(document).ready(() => {
  Attendees.attendingmeetPrintConfiguration.init();
});
