Attendees.directoryPrintConfiguration = {

  init: () => {
    console.log('static/js/persons/directory_print_configuration_view.js');
    Attendees.directoryPrintConfiguration.listenToFormSubmit();
  },

  listenToFormSubmit: () => {
    window.addEventListener('pageshow', (event) => {
      if (event.persisted || performance.getEntriesByType("navigation")[0].type === 'back_forward') {
        console.log('Re-enabling buttons after back ...');
        document.querySelector('div.spinner-border').classList.add('d-none');
        document.querySelector('button[type=submit]').disabled = false;
      }
    });

    document.directoryPrintConfiguration.addEventListener('submit', Attendees.directoryPrintConfiguration.handleSubmitToGeneratePDF);
  },

  handleSubmitToGeneratePDF: (event) => {
    event.preventDefault();

    if (confirm('Do you want to see the directory for print? (This will take 2 minutes.)')) {
      const formData = new FormData(event.target);
      const searchParams = new URLSearchParams(formData);  // encodeURI break UTF8?
      event.target.querySelector('button[type=submit]').disabled = true;
      document.querySelector('div.spinner-border').classList.remove('d-none');
      location.href = `${document.directoryPrintConfiguration.action}?${searchParams}`;
    }
  },
};

$(document).ready(() => {
  Attendees.directoryPrintConfiguration.init();
});
