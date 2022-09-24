Attendees.calendar = {
  contentTypeEndpoint: '',
  contentTypeEndpoints: {},

  init: () => {
    console.log('static/js/occasions/calendar_list_view.js');
    Attendees.calendar.initCalendarSelector();
    Attendees.calendar.initScheduler();
  },

  initCalendarSelector: () => {

  },

  initScheduler: () => {
    $('div#scheduler').dxScheduler(Attendees.calendar.schedulerConfig);
  },

  schedulerConfig: {
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    dataSource: null,
    views: ['day', 'week', 'workWeek', 'month'],
    currentView: 'day',
    showCurrentTimeIndicator: true,
    startDayHour: 9,
    height: '80vh',
  },
};

$(document).ready(() => {
  Attendees.calendar.init();
});
