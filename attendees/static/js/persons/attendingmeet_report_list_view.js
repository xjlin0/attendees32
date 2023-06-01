window.Attendees = {
  attendingmeetReportListView: {
    PausedCategory: '27',  // for pausing counting for attendingmeet report, has to be string
    textStyleFlipper: {
      'line-through': '',
      '': 'line-through',
    },

    init: () => {
      console.log('static/js/persons/attendingmeet_report_list_view.js');
      Attendees.attendingmeetReportListView.startListener();
    },

    startListener: () => {
      const mainDiv = document.querySelector('div.attendingmeet-report-container');
      if (mainDiv) {
        mainDiv.addEventListener('click', (event) => {
        const target = event.target;
          if (target && target.matches('div.member') && target.id) {
            const url =  mainDiv.dataset.url + target.id + '/';
            const currentCategory = target.dataset.category;
            const nextCategory = currentCategory === Attendees.attendingmeetReportListView.PausedCategory ? target.dataset.previousCategory : Attendees.attendingmeetReportListView.PausedCategory;
            const params = {
              method: 'PATCH',
              body: JSON.stringify({category: nextCategory}),
              headers: {
                'Content-Type': 'application/json',
                'X-Target-Attendee-Id': target.dataset.attendeeId,
                'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
              },
            };

            fetch(url, params)
              .then(response => response.json())
              .then(result => {
                target.dataset.previousCategory = currentCategory;
                target.dataset.category = result.category;
                target.style['text-decoration'] = Attendees.attendingmeetReportListView.textStyleFlipper[target.style['text-decoration']];
                target.style.color = target.dataset.category === Attendees.attendingmeetReportListView.PausedCategory ? 'SlateGrey' : 'black';
                target.firstChild.style.display = target.dataset.category === Attendees.attendingmeetReportListView.PausedCategory ? 'None' : 'inline';
              })
              .catch(err => console.log(err));
          }
        }, false);
      } else {
        console.log('report does not exits yet! ');
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
