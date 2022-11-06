Attendees.locationTimeline = {
  scheduler: null,
  calendarSelector: null,
  contentTypeEndpoint: '',
  contentTypeEndpoints: {},

  init: () => {
    console.log('static/js/occasions/location_timeline_list_view.js');
//    Attendees.locationTimeline.initCalendarSelector();
    Attendees.locationTimeline.initScheduler();
    Attendees.locationTimeline.initListeners();
  },

  initListeners: () => {
    window.addEventListener("resize", Attendees.utilities.debounce(250, ()=>{
      Attendees.locationTimeline.scheduler && Attendees.locationTimeline.scheduler.option('useDropDownViewSwitcher', window.innerWidth < 425);
    }))
  },

//  initCalendarSelector: () => {
//    Attendees.locationTimeline.calendarSelector = $('div#calendar-selector').dxSelectBox(Attendees.locationTimeline.calendarSelectorConfig).dxSelectBox('instance');
//  },

 // calendarSelectorConfig: {
 //   valueExpr: 'id',
 //   displayExpr: 'name',
 //   searchEnabled: true,
 //   width: '100%',
 //   value: parseInt(document.querySelector('div#scheduler').dataset.organizationDefaultCalendar),
 //   onValueChanged: (e)=> {
 //     if (e.value && Attendees.locationTimeline.scheduler) {
 //       Attendees.locationTimeline.scheduler.getDataSource().reload()
 //     }
 //   },
 //   dataSource: new DevExpress.data.DataSource({
 //     store: new DevExpress.data.CustomStore({
 //       key: 'id',
 //       load: (searchOpts) => {
 //         const d = new $.Deferred();
 //
 //         const params = {
 //           take: 9999,
 //           distinction: "source",
 //         };
 //
 //         if (searchOpts['searchValue']) {
 //           params['searchValue'] = searchOpts['searchValue'];
 //           params['searchOperation'] = searchOpts['searchOperation'];
 //           params['searchExpr'] = searchOpts['searchExpr'];
 //         }
 //
 //         $.get(document.querySelector('div#scheduler').dataset.calendarsEndpoint, params)
 //           .done((result) => {
 //             d.resolve(result.data);
 //           });
 //
 //         return d.promise();
 //       },
 //       byKey: (key) => {
 //         const d = new $.Deferred();
 //         $.get(document.querySelector('div#scheduler').dataset.calendarsEndpoint + key + '/')
 //           .done((result) => {
 //             d.resolve(result);
 //           });
 //         return d.promise();
 //       },
 //     }),
 //     // key: 'slug',
 //   }),
 // },

  initScheduler: () => {
    Attendees.locationTimeline.scheduler = $('div#timeline').dxScheduler(Attendees.locationTimeline.schedulerConfig).dxScheduler('instance');
  },

  schedulerConfig: {
    startDateExpr: 'start',
    endDateExpr: 'end',
    // textExpr: 'source',
    // descriptionExpr: 'source',

    // appointmentTemplate: https://js.devexpress.com/Demos/WidgetsGallery/Demo/Scheduler/CustomTemplates/jQuery/Light/
    editing: {
      allowUpdating: false,
      allowAdding: false,
      allowDeleting: false,
    },
    dataSource: new DevExpress.data.DataSource({
      store: new DevExpress.data.CustomStore({
        key: 'id',
        load: (searchOpts) => {
          const d = new $.Deferred();
          const params = {
            take: 9999,
            start: Attendees.locationTimeline.scheduler && Attendees.locationTimeline.scheduler.getStartViewDate().toISOString(),
            end: Attendees.locationTimeline.scheduler && Attendees.locationTimeline.scheduler.getEndViewDate().toISOString(),
          };
          // params['calendar'] = Attendees.locationTimeline.calendarSelector ? Attendees.locationTimeline.calendarSelector.option('value') : parseInt(document.querySelector('div#scheduler').dataset.organizationDefaultCalendar);

          if (searchOpts['searchValue']) {
            params['searchValue'] = searchOpts['searchValue'];
            params['searchOperation'] = searchOpts['searchOperation'];
            params['searchExpr'] = searchOpts['searchExpr'];
          }

          $.get(document.querySelector('div#timeline').dataset.occurrencesEndpoint, params)
            .done((result) => {
              result.data.forEach(o => {
                if (o.description && o.description.startsWith('allDay:')){  // magic word to label full day event
                  o['allDay'] = true;
                }
              });
              d.resolve(result.data);
            });

          return d.promise();
        },
        byKey: (key) => {
          const d = new $.Deferred();
          $.get(document.querySelector('div#timeline').dataset.occurrencesEndpoint + key + '/')
            .done((result) => {
              d.resolve(result);
            });
          return d.promise();
        },
        update: (key) => {
          console.log("hi 121 here is key: ", key);
        },  // Custom Template: https://js.devexpress.com/Demos/WidgetsGallery/Demo/Scheduler/CustomTemplates/jQuery/Light/
        insert: (e) => {
          console.log("hi 124 insert here is e: ", e);
        },
        remove: (key) => {
          console.log("hi 127 remove here is key: ", key);
        },
      }),
    }),
    onAppointmentRendered: (e) => {
      if (e.appointmentData && e.appointmentData.color) {
        e.appointmentElement[0].style.backgroundColor = e.appointmentData.color;
      }
    },
    views: [
      {
        type: 'timelineWeek',
        name: 'Week',
        groupOrientation: 'vertical',
      },
      // {
      //   type: 'workWeek',
      //   groupOrientation: 'vertical',
      // },
      // {
      //   type: 'month',
      //   groupOrientation: 'horizontal',
      // },
    ],
    currentView: 'timelineWeek',
    showCurrentTimeIndicator: true,
    useDropDownViewSwitcher: window.innerWidth < 425,
    startDayHour: 8,
    endDayHour: 24,
    cellDuration: 120,
    scrolling: {
      mode: 'virtual',
    },
    height: '80vh',
    groups: ['calendar'],
    resources: [
      {
        fieldExpr: 'calendar',
        displayExpr: "name",
        dataSource: new DevExpress.data.DataSource({
          store: new DevExpress.data.CustomStore({
            key: 'id',
            load: (searchOpts) => {
              const d = new $.Deferred();

              const params = {
                take: 9999,
                distinction: "source",
              };

              $.get(document.querySelector('div#timeline').dataset.calendarsEndpoint, params)
                .done((result) => {
                  d.resolve(result.data);
                });

              return d.promise();
            },
            byKey: (key) => {
              const d = new $.Deferred();
              $.get(document.querySelector('div#timeline').dataset.calendarsEndpoint + key + '/')
                .done((result) => {
                  d.resolve(result);
                });
              return d.promise();
            },
          }),
        }),



      },
    ]
  },
};

$(document).ready(() => {
  Attendees.locationTimeline.init();
});
