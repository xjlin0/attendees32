Attendees.calendar = {
  scheduler: null,
  calendarSelector: null,
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
    Attendees.calendar.calendarSelector = $('div#calendar-selector').dxSelectBox(Attendees.calendar.calendarSelectorConfig).dxSelectBox('instance');
  },

  calendarSelectorConfig: {
    valueExpr: 'id',
    displayExpr: 'name',
    searchEnabled: true,
    width: '100%',
    value: parseInt(document.querySelector('div#scheduler').dataset.organizationDefaultCalendar),
    // onValueChanged: (e)=> {
    //   Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['rollCallListViewOpts'], 'selectedGatheringId', e.value);
    //   Attendees.calendar.filtersForm.validate();
    //   const meet = Attendees.calendar.filtersForm.getEditor('meets').option('value');
    //   if (e.value && meet && Attendees.calendar.attendancesDatagrid) {
    //     Attendees.calendar.scheduler.refresh();
    //   }
    // },
    dataSource: new DevExpress.data.DataSource({
      store: new DevExpress.data.CustomStore({
        key: 'id',
        load: (searchOpts) => {
          const d = new $.Deferred();

          const params = {
            take: 9999,
            distinction: "source",
          };

          if (searchOpts['searchValue']) {
            params['searchValue'] = searchOpts['searchValue'];
            params['searchOperation'] = searchOpts['searchOperation'];
            params['searchExpr'] = searchOpts['searchExpr'];
          }

          $.get(document.querySelector('div#scheduler').dataset.calendarsEndpoint, params)
            .done((result) => {
              d.resolve(result.data);
            });

          return d.promise();
        },
        byKey: (key) => {
          const d = new $.Deferred();
          $.get(document.querySelector('div#scheduler').dataset.calendarsEndpoint + key + '/')
            .done((result) => {
              d.resolve(result);
            });
          return d.promise();
        },
      }),
      // key: 'slug',
    }),
  },

  initScheduler: () => {
    Attendees.calendar.scheduler = $('div#scheduler').dxScheduler(Attendees.calendar.schedulerConfig).dxScheduler('instance');
  },

  schedulerConfig: {
    startDateExpr: 'start',
    endDateExpr: 'end',
    // textExpr: 'source',
    // descriptionExpr: 'source',
    dataSource: new DevExpress.data.DataSource({
      store: new DevExpress.data.CustomStore({
        key: 'id',
        load: (searchOpts) => {
          const d = new $.Deferred();
          const params = {
            start: searchOpts.dxScheduler.startDate.toISOString(),
            end: searchOpts.dxScheduler.endDate.toISOString(),
          };
          params['calendar'] = Attendees.calendar.calendarSelector ? Attendees.calendar.calendarSelector.option('value') : parseInt(document.querySelector('div#scheduler').dataset.organizationDefaultCalendar);

          if (searchOpts['searchValue']) {
            params['searchValue'] = searchOpts['searchValue'];
            params['searchOperation'] = searchOpts['searchOperation'];
            params['searchExpr'] = searchOpts['searchExpr'];
          }

          $.get(document.querySelector('div#scheduler').dataset.occurrencesEndpoint, params)
            .done((result) => {
              d.resolve(result.data);
            });

          return d.promise();
        },
        byKey: (key) => {
          const d = new $.Deferred();
          $.get(document.querySelector('div#scheduler').dataset.occurrencesEndpoint + key + '/')
            .done((result) => {
              d.resolve(result);
            });
          return d.promise();
        },
      }),
    }),
    views: ['agenda', 'day', 'week', 'month'],
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
