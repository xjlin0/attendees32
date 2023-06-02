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
      const mainDiv = document.querySelector('body');
      let timer;
      if (mainDiv) {
        mainDiv.addEventListener('click', (event) => {
          if (event.detail < 2) {
            timer = setTimeout(() => {
              Attendees.attendingmeetReportListView.patchMember(event.target, mainDiv.dataset.url, false);
            }, 400)
          }
        }, false);

        mainDiv.addEventListener('dblclick', (event) => {
          clearTimeout(timer);
          Attendees.attendingmeetReportListView.patchMember(event.target, mainDiv.dataset.url, true);
        }, false);

      } else {
        console.log('The report does not rendered yet! ');
      }
    },

    patchMember: (target, endpoint, note) => {
      if (target && target.matches('div.member') && target.id) {
        target.style.backgroundColor = 'Green';
        let message = null;
        if (note){
          const action = target.dataset.category === Attendees.attendingmeetReportListView.PausedCategory ? 'unpausing' : 'pausing';
          message = prompt(`Please enter the optional participation note for ${action}, click cancel to abort changing.`, target.title);
          if (message === null) {
            target.style.backgroundColor = null;
            return;
          }
        }

        const url =  endpoint + target.id + '/';
        const currentCategory = target.dataset.category;
        const nextCategory = currentCategory === Attendees.attendingmeetReportListView.PausedCategory ? target.dataset.previousCategory : Attendees.attendingmeetReportListView.PausedCategory;
        const body = {category: nextCategory};
        if (message) body.infos = {note: message};
        const params = {
          method: 'PATCH',
          body: JSON.stringify(body),
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
            target.title = result.infos.note || '';
//            target.style['text-decoration'] = Attendees.attendingmeetReportListView.textStyleFlipper[target.style['text-decoration']];
//            target.style.color = target.dataset.category === Attendees.attendingmeetReportListView.PausedCategory ? 'SlateGrey' : 'black';
//            target.firstChild.style.display = target.dataset.category === Attendees.attendingmeetReportListView.PausedCategory ? 'None' : 'inline';
            if (target.dataset.category === Attendees.attendingmeetReportListView.PausedCategory) {
              target.firstChild.style.display = 'None';
              target.classList.add('paused');
            } else {
              target.firstChild.style.display = 'inline';
              target.classList.remove('paused');
            }
            target.style.backgroundColor = null;
          })
          .catch(err => {
            alert(`Updating AttendingMeet ${target.id} error: `, err);
            target.style.backgroundColor = 'Red';
          });
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
