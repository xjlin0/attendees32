window.Attendees = {
  attendingmeetReportListView: {

    PausedCategory: 27,  // for pausing counting for attendingmeet report
    ScheduledCategory: 1,

    init: () => {
      console.log('static/js/persons/attendingmeet_report_list_view.js');
    },
  }
};

document.addEventListener('DOMContentLoaded', () => {
   Attendees.attendingmeetReportListView.init();
}, false);
