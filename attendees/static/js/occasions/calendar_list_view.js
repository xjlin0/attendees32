Attendees.calendar = {
  scheduler: null,
  contentTypeEndpoint: '',
  contentTypeEndpoints: {},

  init: () => {
    console.log('static/js/occasions/calendar_list_view.js');
    Attendees.calendar.initCalendarSelector();
    Attendees.calendar.initScheduler();
    Attendees.calendar.initListeners();
  },

  initListeners: () => {
    window.addEventListener("resize", Attendees.utilities.debounce(250, ()=>{
      Attendees.calendar.scheduler && Attendees.calendar.scheduler.option('useDropDownViewSwitcher', window.innerWidth < 425);
    }))
  },

  initCalendarSelector: () => {

  },

  initScheduler: () => {
    Attendees.calendar.scheduler = $('div#scheduler').dxScheduler(Attendees.calendar.schedulerConfig).dxScheduler('instance');
  },

  schedulerConfig: {
    // timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    dataSource: null,
    views: ['day', 'week', 'month'],
    currentView: 'day',
    showCurrentTimeIndicator: true,
    useDropDownViewSwitcher: window.innerWidth < 425,
    startDayHour: 7,
    endDayHour: 21,
    height: '80vh',
  },
};

$(document).ready(() => {
  Attendees.calendar.init();
});
