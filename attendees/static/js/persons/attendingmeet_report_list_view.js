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
      Attendees.attendingmeetReportListView.counterPrompt();
    },

    startListener: () => {  // for click to pause and double click to edit notes
      const mainDiv = document.querySelector('body');
      let timer;
      if (mainDiv) {
        mainDiv.addEventListener('click', (event) => {
          if (event.detail < 2) {
            timer = setTimeout(() => {
              Attendees.attendingmeetReportListView.patchMember(event.target, mainDiv.dataset.url, false);
            }, 400)  // to distinguish single or double click
          }
        }, false);  // single click to toggle scheduled/pause

        mainDiv.addEventListener('dblclick', (event) => {
          clearTimeout(timer);
          Attendees.attendingmeetReportListView.patchMember(event.target, mainDiv.dataset.url, true);
        }, false);  // double click to pause with note

      } else {
        console.log('The report does not rendered yet! ');
      }
    },

    counterPrompt: () => {
      setTimeout(() => {
        const familyCount = document.querySelectorAll('div.family-name').length;
        const totalAttendeeCount = document.querySelectorAll('div.member[data-attendee-id]').length;
        const pausedAttendeeCount = document.querySelectorAll('div.member.paused[data-attendee-id]').length;
        const activeAttendeeCount = totalAttendeeCount - pausedAttendeeCount;
        alert(`Total: ${totalAttendeeCount} live attendees in ${familyCount} families, including ${pausedAttendeeCount} paused attendees and ${activeAttendeeCount} active attendees.` );
      }, 400)
    },

    patchMember: (target, endpoint, note) => {
      if (target && target.matches('div.member') && target.id) {
        target.style.backgroundColor = 'Green';
        let message = null;
        if (note){
          message = prompt(`Please enter the participation note, click cancel to abort.`, target.title);
          if (message === null) {
            target.style.backgroundColor = null;
            return;
          }
        }

        const url =  endpoint + target.id + '/';
        const currentCategory = target.dataset.category;
        const nextCategory = note ? currentCategory : (currentCategory === Attendees.attendingmeetReportListView.PausedCategory ? target.dataset.previousCategory : Attendees.attendingmeetReportListView.PausedCategory);
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
            target.title = (result.infos && result.infos.note) ? result.infos.note : '';
            
            if (target.dataset.category === Attendees.attendingmeetReportListView.PausedCategory) {
              target.style.textDecoration = 'line-through';
              target.style.color = 'SlateGrey';
              target.querySelector('span.count').style.display = 'None';
              target.classList.add('paused');
            } else {
              target.style.textDecoration = '';
              target.style.color = 'black';
              target.querySelector('span.count').style.display = 'inline';
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
