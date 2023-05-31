window.Attendees = {
  attendingmeetReportListView: {

    PausedCategory: 27,  // for pausing counting for attendingmeet report
    ScheduledCategory: 1,

    init: () => {
      console.log('static/js/persons/attendingmeet_report_list_view.js');
      Attendees.attendingmeetReportListView.startListener();
    },

    startListener: () => {
      const mainDiv = document.querySelector('div.attendingmeet-report-container');
      if (mainDiv) {
        mainDiv.addEventListener('click', (event) => {
        console.log('clicked  and here is the id: ', event.target.id);
          if (event.target.matches('div.member') && event.target.id) {
              console.log('clicked!');
          }
        }, false);

      } else {
        console.log('report does not exits! ');
      }
    },

    mustRunLast: () => {  // https://stackoverflow.com/a/74956907/4257237
      if (!document.querySelector('div.attendingmeet-report-container')) {
        setTimeout(Attendees.attendingmeetReportListView.mustRunLast, 100);
        return;
      }
      Attendees.attendingmeetReportListView.init();
    },
  }
};

document.addEventListener('load', Attendees.attendingmeetReportListView.mustRunLast());
