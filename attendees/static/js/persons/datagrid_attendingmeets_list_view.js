Attendees.attendingmeets = {
  filtersForm: null,
  meetScheduleRules: {},
  selectedMeetHasRule: false,
  initialized: false,
  filterMeetCheckbox: null,
  contentTypeEndpoint: '',
  contentTypeEndpoints: {},
  init: () => {
    console.log('static/js/persons/datagrid_attendingmeets_list_view.js');
    Attendees.attendingmeets.initFilterMeetCheckbox();
    Attendees.attendingmeets.initEditingSwitch();
    Attendees.attendingmeets.initFiltersForm();
    // Attendees.attendingmeets.initNewAttendeeButton();
  },

  initEditingSwitch: () => {
    $('div#custom-control-edit-switch').dxSwitch({
      value: Attendees.utilities.editingEnabled,
      switchedOffText: 'Editing disabled',
      switchedOnText: 'Editing enabled',
      hint: 'Toggle Editing mode',
      width: '18%',
      height: '110%',
      onValueChanged: (e) => {  // not reconfirm, it's already after change
        Attendees.utilities.editingEnabled = e.value;
        Attendees.attendingmeets.toggleEditing(e.value);
      },
    })
  },

  initFilterMeetCheckbox: () => {
    Attendees.attendingmeets.filterMeetCheckbox = $('div#custom-control-filter-meets-checkbox').dxCheckBox({
      value: true,
      hint: 'When checked, the dropdown list of Meets will be filtered based on the From/Till date&time',
      text: 'Filter meets by date/time',
      onValueChanged: (e) => {
        Attendees.attendingmeets.filtersForm.getEditor('meets').getDataSource().reload();
      }
    }).dxCheckBox('instance');
  },

  // initNewAttendeeButton: () => {
  //   Attendees.attendingmeets.newAttendeeButton = $('div#new-attendee').dxButton({
  //     text: "+ Attendee",
  //     type: "success",
  //     icon: "fas fa-user-plus",
  //     // height: '50%',
  //     stylingMode: "outlined",
  //   });
  // },

  toggleEditing: (enabled) => {
    if (Attendees.attendingmeets.atteningmeetsDatagrid) {
      Attendees.attendingmeets.atteningmeetsDatagrid.option('editing.allowUpdating', enabled);
      Attendees.attendingmeets.atteningmeetsDatagrid.option('editing.allowAdding', enabled);
      Attendees.attendingmeets.atteningmeetsDatagrid.option('editing.allowDeleting', enabled);
      Attendees.attendingmeets.atteningmeetsDatagrid.option('editing.popup.onContentReady', e => e.component.option('toolbarItems[0].visible', enabled));
    }
  },

  initFiltersForm: () => {
    $.ajaxSetup({
      headers: {
        'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
      }
    });
    Attendees.attendingmeets.filtersForm = $('form.filters-dxform').dxForm(Attendees.attendingmeets.filterFormConfigs).dxForm('instance');
  },

  filterFormConfigs: {
    dataSource: null,
    colCount: 12,
    itemType: 'group',
    items: [
      {
        colSpan: 3,
        cssClass: 'filter-from',
        dataField: 'filter-from',
        helpText: 'required to generate attendingmeets',
        validationRules: [{
          reevaluate: true,
          type: 'custom',
          message: 'filter date "Till" is earlier than "From"',
          validationCallback: (e) => {
            const filterTill = $('div.filter-till input')[1].value;
            return e.value && filterTill ? new Date(filterTill) > e.value : true;
          },  // allow null for users to check all records
        }],
        label: {
          location: 'top',
          text: 'From (mm/dd/yyyy)',
        },
        editorType: 'dxDateBox',
        editorOptions: {
          showClearButton: true,
          value: new Date(new Date().setHours(new Date().getHours() - 1)),
          type: 'datetime',
          onValueChanged: (e) => {
            // Attendees.attendingmeets.generateGatheringsButton.option('disabled', !Attendees.attendingmeets.readyToGenerate());
            if (Attendees.attendingmeets.filterMeetCheckbox.option('value')) {
              Attendees.attendingmeets.filtersForm.getEditor('meets').getDataSource().reload();
            }
            const meets = $('div.selected-meets select').val();
            if (meets.length) {
              Attendees.attendingmeets.attendingmeetsDatagrid.refresh();
            }
          },
        },
      },
      {
        colSpan: 3,
        cssClass: 'filter-till',
        dataField: 'filter-till',
        helpText: 'required to generate attendingmeets',
        validationRules: [{
          reevaluate: true,
          type: 'custom',
          message: 'filter date "Till" is earlier than "From"',
          validationCallback: (e) => {
            const filterFrom = $('div.filter-from input')[1].value;
            return e.value && filterFrom ? new Date(filterFrom) < e.value : true;
          },  // allow null for users to check all records
        }],
        label: {
          location: 'top',
          text: 'Till(exclude)',
        },
        editorType: 'dxDateBox',
        editorOptions: {
          showClearButton: true,
          value: new Date(new Date().setMonth(new Date().getMonth() + 1)),
          type: 'datetime',
          onValueChanged: (e) => {
            Attendees.attendingmeets.generateGatheringsButton.option('disabled', !Attendees.gatherings.readyToGenerate());
            if (Attendees.attendingmeets.filterMeetCheckbox.option('value')) {
              Attendees.attendingmeets.filtersForm.getEditor('meets').getDataSource().reload();
            }  // allow users to screen only active meets by meet's start&finish
            const meets = $('div.selected-meets select').val();
            if (meets.length) {
              Attendees.attendingmeets.attendingmeetsDatagrid.refresh();
            }
          },
        },
      },
      {
        dataField: 'meets',
        colSpan: 6,
        helpText: 'Select single one to view/generate gatherings, or multiple one to view',
        cssClass: 'selected-meets',
        validationRules: [{type: 'required'}],
        label: {
          location: 'top',
          text: 'Select activities(meets)',
        },
        editorType: 'dxTagBox',
        editorOptions: {
          valueExpr: 'slug',
          displayExpr: 'display_name',
          showClearButton: true,
          searchEnabled: false,
          buttons:[
            'clear',
            {
              name: 'selectAll',
              stylingMode: 'outlined',
              location: 'after',
              options: {
                icon: 'fas fa-solid fa-check-double',
                type: 'default',
                elementAttr: {
                  title: 'select all meets',
                },
                onClick() {
                  Attendees.attendingmeets.selectAllGroupedTags('meets');
                },
              },
            }
          ],
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
          onValueChanged: (e)=> {
            console.log("hi 182 onValueChanged, e: ", e);
            Attendees.attendingmeets.filtersForm.validate();
            const defaultHelpText = 'Select single one to view/generate gatherings, or multiple one to view';
            const $meetHelpText = Attendees.attendingmeets.filtersForm.getEditor('meets').element().parent().parent().find(".dx-field-item-help-text");
            Attendees.attendingmeets.selectedMeetHasRule = false;
            // Attendees.attendingmeets.generateGatheringsButton.option('disabled', true);
            $meetHelpText.text(defaultHelpText);  // https://supportcenter.devexpress.com/ticket/details/t531683
            if (e.value && e.value.length > 0) {
              Attendees.attendingmeets.attendingmeetsDatagrid.refresh();
              if (e.value.length < 2) {
                const newHelpTexts = [];
                let finalHelpText = '';
                let lastDuration = 0;
                const noRuleText = 'This meet does not have schedules in EventRelation';
                const ruleData = Attendees.attendingmeets.meetScheduleRules[ e.value[0] ];
                const timeRules = ruleData.rules;
                const meetStart = new Date(ruleData.meetStart).toDateString();
                const meetFinish = new Date(ruleData.meetFinish).toDateString();
                if (timeRules && timeRules.length > 0) {
                  timeRules.forEach(timeRule => {
                    if (timeRule.rule) {
                      Attendees.attendingmeets.selectedMeetHasRule = true;
                      const toLocaleStringOpts = Attendees.utilities.timeRules[timeRule.rule];
                      const startTime = new Date(timeRule.start);
                      const endTime = new Date(timeRule.end);
                      const startTimeText = startTime.toLocaleString(navigator.language, toLocaleStringOpts);
                      const endTimeText = endTime.toLocaleString(navigator.language, toLocaleStringOpts);
                      lastDuration = ( endTime - startTime )/60000;
                      newHelpTexts.push(timeRule.rule + ' ' + startTimeText + ' ~ ' + endTimeText + '@' + timeRule.location);
                    } else {
                      newHelpTexts.push(noRuleText);
                    }
                  });
                  finalHelpText = newHelpTexts.join(', ') + ' from ' + meetStart + ' to ' + meetFinish;
                  if (Attendees.attendingmeets.selectedMeetHasRule && $('div#custom-control-edit-switch').dxSwitch('instance').option('value') && lastDuration > 0) {
                    Attendees.attendingmeets.generateGatheringsButton.option('disabled', false);
                  }
                } else {
                  finalHelpText = noRuleText;
                }
                $meetHelpText.text(finalHelpText);  // https://supportcenter.devexpress.com/ticket/details/t531683
                Attendees.attendingmeets.filtersForm.itemOption('duration', {editorOptions: {value: lastDuration}});
              }
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {};

                if (Attendees.attendingmeets.filterMeetCheckbox.option('value')) {
                  const filterFrom = $('div.filter-from input')[1].value;
                  const filterTill = $('div.filter-till input')[1].value;
                  params['start'] = filterFrom ? new Date(filterFrom).toISOString() : null;
                  params['finish'] = filterTill ? new Date(filterTill).toISOString() : null;
                  params['grouping'] = 'assembly_name';  // for grouped: true,
                }
                return $.getJSON($('form.filters-dxform').data('meets-endpoint-by-slug'), params);
              },
            }),
            key: 'slug',
          }),
        },
      },
      {
        dataField: 'characters',
        colSpan: 12,
        helpText: 'Select one or more characters to filter results',
        cssClass: 'selected-characters',
        validationRules: [{type: 'required'}],
        label: {
          location: 'top',
          text: 'Select characters',
        },
        editorType: 'dxTagBox',
        editorOptions: {
          valueExpr: 'slug',
          displayExpr: 'display_name',
          showClearButton: true,
          searchEnabled: false,
          buttons:[
            'clear',
            {
              name: 'selectAll',
              stylingMode: 'outlined',
              location: 'after',
              options: {
                icon: 'fas fa-solid fa-check-double',
                type: 'default',
                elementAttr: {
                  title: 'select all characters',
                },
                onClick() {
                  Attendees.attendingmeets.selectAllGroupedTags('characters');
                },
              },
            }
          ],
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
          onValueChanged: (e)=> {
            // Attendees.attendingmeets.filtersForm.validate();
            // const defaultHelpText = 'Select single one to view/generate gatherings, or multiple one to view';
            // const $meetHelpText = Attendees.attendingmeets.filtersForm.getEditor('meets').element().parent().parent().find(".dx-field-item-help-text");
            // Attendees.attendingmeets.selectedMeetHasRule = false;
            // // Attendees.attendingmeets.generateGatheringsButton.option('disabled', true);
            // $meetHelpText.text(defaultHelpText);  // https://supportcenter.devexpress.com/ticket/details/t531683
            if (e.value && e.value.length > 0 && Attendees.attendingmeets.attendingmeetsDatagrid) {
              Attendees.attendingmeets.attendingmeetsDatagrid.refresh();
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {};
                if (Attendees.attendingmeets.filterMeetCheckbox.option('value')) {
                  params['grouping'] = 'assembly_name';  // for grouped: true,
                }
                $.get($('form.filters-dxform').data('characters-endpoint'), params)
                  .done((result) => {
                    d.resolve(result.data);
                    Attendees.attendingmeets.selectAllGroupedTags('characters');
                  });
                return d.promise();
              },
            }),
            key: 'slug',
          }),
        },
      },
      {
        colSpan: 12,
        dataField: "filtered_gathering_set",
        label: {
          location: 'top',
          text: ' ',  // empty space required for removing label
          showColon: false,
        },
        template: (data, itemElement) => {
          Attendees.attendingmeets.attendingmeetsDatagrid = Attendees.attendingmeets.initFilteredAttendingmeetsDatagrid(data, itemElement);
        },
      },
    ],
  },

  selectAllGroupedTags: (editorName) => {
    const availableTagsDxTagBox = Attendees.attendingmeets.filtersForm.getEditor(editorName);
    const availableTagSlugs = availableTagsDxTagBox.option('items').flatMap(assembly => assembly.items.map(item => item.slug));
    availableTagsDxTagBox.option('value', availableTagSlugs);
  },  // loop in loop because of options grouped by assembly

  initFilteredAttendingmeetsDatagrid: (data, itemElement) => {
    const $attendingmeetDatagrid = $("<div id='gatherings-datagrid-container'>").dxDataGrid(Attendees.attendingmeets.gatheringDatagridConfig);
    itemElement.append($attendingmeetDatagrid);
    return $attendingmeetDatagrid.dxDataGrid('instance');
  },

  attendingmeetDatagridConfig: {
    dataSource: {
      store: new DevExpress.data.CustomStore({
        key: 'id',
        load: (loadOptions) => {
          const meets = $('div.selected-meets select').val();
          const deferred = $.Deferred();
          const args = {
            meets: meets,
            start: $('div.filter-from input')[1].value ? new Date($('div.filter-from input')[1].value).toISOString() : null,
            finish: $('div.filter-till input')[1].value ? new Date($('div.filter-till input')[1].value).toISOString() : null,
          };

          [
            'skip',
            'take',
            'requireTotalCount',
            'requireGroupCount',
            'sort',
            'filter',
            'totalSummary',
            'group',
            'groupSummary',
          ].forEach((i) => {
              if (i in loadOptions && Attendees.utilities.isNotEmpty(loadOptions[i]))
                  args[i] = JSON.stringify(loadOptions[i]);
          });

          $.ajax({
            url: $('form.filters-dxform').data('gatherings-endpoint'),
            dataType: "json",
            data: args,
            success: (result) => {
              deferred.resolve(result.data, {
                totalCount: result.totalCount,
                summary:    result.summary,
                groupCount: result.groupCount,
              });
            },
            error: () => {
              deferred.reject("Data Loading Error, probably time out?");
            },
            timeout: 60000,
          });

          return deferred.promise();
        },
        byKey: (key) => {
          const d = new $.Deferred();
          $.get($('form.filters-dxform').data('attendingmeets-endpoint') + key + '/')
            .done((result) => {
              d.resolve(result.data);
            });
          return d.promise();
        },
        update: (key, values) => {
          return $.ajax({
            url: $('form.filters-dxform').data('attendingmeets-endpoint') + key + '/',
            method: 'PATCH',
            dataType: 'json',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(values),
            success: (result) => {
              DevExpress.ui.notify(
                {
                  message: 'update success',
                  width: 500,
                  position: {
                    my: 'center',
                    at: 'center',
                    of: window,
                  },
                }, 'success', 2000);
            },
          });
        },
        insert: function (values) {
          return $.ajax({
            url: $('form.filters-dxform').data('attendingmeets-endpoint'),
            method: 'POST',
            dataType: 'json',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(values),  // ...subject}),
            success: (result) => {
              DevExpress.ui.notify(
                {
                  message: 'Create success',
                  width: 500,
                  position: {
                    my: 'center',
                    at: 'center',
                    of: window,
                  },
                }, 'success', 2000);
            },
          });
        },
        remove: (key) => {
          return $.ajax({
            url: $('form.filters-dxform').data('attendingmeets-endpoint') + key ,
            method: 'DELETE',
            success: (result) => {
              DevExpress.ui.notify(
                {
                  message: 'removed success',
                  width: 500,
                  position: {
                    my: 'center',
                    at: 'center',
                    of: window,
                  },
                }, 'info', 2000);
            },
          });
        },
      }),
    },
    allowColumnReordering: true,
    columnAutoWidth: true,
    allowColumnResizing: true,
    columnResizingMode: 'nextColumn',
    // cellHintEnabled: true,
    hoverStateEnabled: true,
    rowAlternationEnabled: true,
    remoteOperations: true,
    paging: {
      pageSize: 20,
    },
    pager: {
      visible: true,
      allowedPageSizes: [20, 100, 9999],
      showPageSizeSelector: true,
      showInfo: true,
      showNavigationButtons: true,
    },
    stateStoring: {
      enabled: true,
      type: "sessionStorage",
      storageKey: "attendeesAttendingmeetsList",
    },
    loadPanel: {
      message: 'Fetching...',
      enabled: true,
    },
    wordWrapEnabled: false,
    width: '100%',
     grouping: {
       autoExpandAll: true,
     },
     groupPanel: {
       visible: 'auto',
     },  // remoteOperations need server grouping https://js.devexpress.com/Documentation/Guide/Data_Binding/Specify_a_Data_Source/Custom_Data_Sources/#Load_Data/Server-Side_Data_Processing
    columnChooser: {
      enabled: true,
      mode: 'select',
    },
    editing: {
      allowUpdating: false,
      allowAdding: false,
      allowDeleting: false,
      texts: {
        confirmDeleteMessage: 'Are you sure to delete it and all its attendances? Instead, setting the "finish" date is usually enough!',
      },
      mode: 'popup',
      popup: {
        showTitle: true,
        title: 'attendingmeetEditingArgs',
        onContentReady: e => e.component.option('toolbarItems[0].visible', false),
      },
      form: {
        colCount: 2,
        items: [
          {
            dataField: 'meet',
            helpText: "What's the event?",
          },
          {
            dataField: 'display_name',
            helpText: 'Event name and date',
          },
          {
            dataField: 'start',
            helpText: 'Event start time in browser timezone',
          },
          {
            dataField: 'finish',
            helpText: 'Event end time in browser timezone',
          },
          {
            dataField: 'site_type',
            helpText: 'More specific/smaller place preferred',
          },
          {
            dataField: 'site_id',
            helpText: 'Where the event be hold',
//            cssClass: 'in-popup-site-id',
          },
        ],
      },
    },
    onCellClick: (e) => {
        if (e.rowType === 'data' && e.column.dataField === 'display_name') {
            e.component.editRow(e.row.rowIndex);
        }
    },
    onInitNewRow: (rowData) => {
      Attendees.attendingmeets.gatheringsDatagrid.option('editing.popup.title', 'Adding Gathering');
    },
    onEditingStart: (e) => {
      if (e.data && typeof e.data === 'object') {
        Attendees.attendingmeets.contentTypeEndpoint = Attendees.attendingmeets.contentTypeEndpoints[e.data['site_type']];
        const prefix = Attendees.utilities.editingEnabled ? 'Editing: ' : 'Info: ';
        Attendees.attendingmeets.gatheringsDatagrid.option('editing.popup.title', prefix + e.data['gathering_label'] + '@' + e.data['site']);
      }
    },
    onEditorPrepared: (e) => {
      if (e.dataField === 'site_id') {
        Attendees.attendingmeets.siteIdElement = e;
      }
    },
    columns: [
      {
        dataField: 'meet',
        width: '10%',
        validationRules: [{type: 'required'}],
        editorOptions: {
          placeholder: 'Example: "The Rock"',
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: () => {
                const d = new $.Deferred();
                $.get($('form.filters-dxform').data('meets-endpoint-by-id'))
                  .done((result) => {
                    if (Object.keys(Attendees.attendingmeets.meetScheduleRules).length < 1 && result.data && result.data[0]) {
                      result.data.forEach(meet=>{
                        Attendees.attendingmeets.meetScheduleRules[meet.slug] = {meetStart: meet.start, meetFinish: meet.finish, rules: meet.schedule_rules};
                      }); // schedule rules needed for attendingmeets generation
                    }
                    d.resolve(result.data);
                  });
                return d.promise();
              },
              byKey: (key) => {
                return $.getJSON($('form.filters-dxform').data('meets-endpoint-by-id') + key + '/');},
            }),
          },
        },
      },
      {
        dataField: 'display_name',
        width: '30%',
//        visible: false,
        editorOptions: {
          placeholder: 'Example: "The Rock - 12/25/2022"',
        },
        cellTemplate: (cellElement, cellInfo) => {
          cellElement.append ('<u class="text-info">' + cellInfo.data.display_name + '</u>');
        },
      },
      {
        dataField: 'site',
        width: '30%',
        readOnly: true,
        caption: 'Location (only grouped not sorted)',
      },
      {
        dataField: 'start',
        width: '30%',
        validationRules: [{type: 'required'}],
        dataType: 'datetime',
        format: 'longDateLongTime',
        editorOptions: {
          type: 'datetime',
          placeholder: 'Click calendar to select date/time ⇨ ',
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        },
      },
      {
        dataField: 'finish',
        visible: false,
        caption: 'End',
        validationRules: [{type: 'required'}],
        dataType: 'datetime',
        format: 'longDateLongTime',
        editorOptions: {
          type: 'datetime',
          placeholder: 'Click calendar to select date/time ⇨ ',
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        },
      },
//      {
//        dataField: 'site_type',
//        visible: false,
//        caption: 'Location type',
//        validationRules: [{type: 'required'}],
//        editorOptions: {
//          placeholder: 'Example: "room"',
//        },
//        setCellValue: (rowData, value) => {
//          rowData.site_id = undefined;
//          Attendees.attendingmeets.contentTypeEndpoint = Attendees.attendingmeets.contentTypeEndpoints[value];
//          rowData.site_type = value;
////          $('div.in-popup-site-id input')[1].value=''; Todo 20210814: can't clear site_id dxlookup after it reload
////          Attendees.attendingmeets.siteIdElement.value = undefined;
//        },
//        lookup: {
//          hint: 'select a location type',
//          valueExpr: 'id',
//          displayExpr: (rowData) => rowData.model + ': ' + rowData.hint,
//          dataSource: {
//            store: new DevExpress.data.CustomStore({
//              key: 'id',
//              load: (searchOpts) => {
//                const d = new $.Deferred();
//                $.get($('form.filters-dxform').data('content-type-models-endpoint'), {query: 'location'})
//                  .done((result) => {
//                    Attendees.attendingmeets.contentTypeEndpoints = result.data.reduce((obj, item) => ({...obj, [item.id]: item.endpoint}) ,{});
//                    d.resolve(result.data);
//                  });
//                return d.promise();
//              },
//              byKey: (key) => {
//                const d = new $.Deferred();
//                $.get($('form.filters-dxform').data('content-type-models-endpoint') + key + '/', {query: 'location'})
//                  .done((result) => {
//                    if (result.data && result.data[0] && result.data[0].endpoint) {
//                      Attendees.attendingmeets.contentTypeEndpoint = result.data[0].endpoint;
//                    }
//                    d.resolve(result.data);
//                  });
//                return d.promise();
//              },
//            }),
//          },
//        },
//      },
//      {
//        dataField: 'site_id',
//        visible: false,
//        cssClass: 'pre-popup-site-id',
//        caption: 'Location',
//        validationRules: [{type: 'required'}],
//        editorOptions: {
//          placeholder: 'Example: "Fellowship F201"',
//        },
//        lookup: {
//          allowClearing: true,
//          hint: 'select a location',
//          valueExpr: 'id',
//          displayExpr: 'display_name',
//          dataSource: {
//            store: new DevExpress.data.CustomStore({
//              key: 'id',
//              load: (searchArgs) => {
//                if (Attendees.gatherings.contentTypeEndpoint) {
//                  const d = new $.Deferred();
//                  $.get(Attendees.gatherings.contentTypeEndpoint, searchArgs)
//                    .done((result) => {
//                      d.resolve(result.data);
//                    });
//                  return d.promise();
//                }
//              },
//              byKey: (key) => {
//                if (Attendees.gatherings.contentTypeEndpoint) {
//                  const d = new $.Deferred();
//                  $.get(Attendees.gatherings.contentTypeEndpoint + key + '/')
//                    .done((result) => {
//                    if (result && result.id && parseInt(key) === result.id) {
//                      result.id = key;
//                    }  // Todo: type conversion for integer key of models other than address?
//                      d.resolve(result);
//                    });
//                  return d.promise();
//                }
//              },
//            }),
//          },
//        },
//      },
    ],
  },
};

$(document).ready(() => {
  Attendees.attendingmeets.init();
});
