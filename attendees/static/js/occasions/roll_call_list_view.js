Attendees.rollCall = {
  filtersForm: null,
  meetScheduleRules: {},
  selectedMeetHasRule: false,
  initialized: false,
  filterMeetCheckbox: null,
  loadOptions: null,
  selectedCharacterSlugs: [],
  selectedMeetSlugs: [],
  meetData: {},
  init: () => {
    console.log('static/js/occasions/roll_call_list_view.js');
//    Attendees.utilities.clearGridStatesInSessionStorage(Attendees.utilities.datagridStorageKeys['rollCallListView']); // remove saved search text without interfering column visibility
//    Attendees.rollCall.initFilterMeetCheckbox();
//    Attendees.rollCall.initEditingSwitch();
    Attendees.rollCall.initFiltersForm();
  },

  initFiltersForm: () => {
    $.ajaxSetup({
      headers: {
        'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
      }
    });
    Attendees.rollCall.filtersForm = $('form.filters-dxform').dxForm(Attendees.rollCall.filterFormConfigs).dxForm('instance');
    Attendees.rollCall.filtersForm.getEditor('meets').getDataSource().reload();
  },

  filterFormConfigs: {
    dataSource: null,
    colCount: 12,
    itemType: 'group',
    items: [
      {
        dataField: 'meets',
        colSpan: 12,
        helpText: "Can't show schedules yet. Select one to view its schedules",
        cssClass: 'selected-meets',
        validationRules: [{type: 'required'}],
        label: {
          location: 'top',
          text: 'Select activity(meet)',
        },
        editorType: 'dxSelectBox',
        editorOptions: {
          valueExpr: 'slug',
          displayExpr: 'display_name',
//          showClearButton: true,
          searchEnabled: false,
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
          onValueChanged: (e)=> {
            Attendees.rollCall.filtersForm.validate();
            const defaultHelpText = "Can't show schedules when multiple selected. Select single one to view its schedules.";
            const $meetHelpText = Attendees.rollCall.filtersForm.getEditor('meets').element().parent().parent().find(".dx-field-item-help-text");
            Attendees.rollCall.selectedMeetHasRule = false;
            $meetHelpText.text(defaultHelpText);  // https://supportcenter.devexpress.com/ticket/details/t531683

            if (e.value) {
              Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['rollCallListViewOpts'], 'selectedMeetSlugs', e.value);
              Attendees.rollCall.attendancesDatagrid.refresh();
              const newHelpTexts = [];
              let finalHelpText = '';
              let lastDuration = 0;
              const noRuleText = 'This meet does not have schedules in EventRelation';
              const ruleData = Attendees.rollCall.meetScheduleRules[ e.value ];
              const timeRules = ruleData.rules;
              const meetStart = new Date(ruleData.meetStart).toDateString();
              const meetFinish = new Date(ruleData.meetFinish).toDateString();
              if (timeRules && timeRules.length > 0) {
                timeRules.forEach(timeRule => {
                  if (timeRule.rule) {
                    Attendees.rollCall.selectedMeetHasRule = true;
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
              } else {
                finalHelpText = noRuleText;
              }
              $meetHelpText.text(finalHelpText);  // https://supportcenter.devexpress.com/ticket/details/t531683
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {
                  start: new Date(new Date().setHours(new Date().getHours() - 1)).toISOString(),
                  finish: new Date(new Date().setDate(new Date().getDate() + 5)).toISOString(),
                  grouping: 'assembly_name',  // for grouped: true
                  model: 'attendance',  // for suppressing no-attendance meets such as believe
                };

                $.get($('form.filters-dxform').data('meets-endpoint-by-slug'), params)
                  .done((result) => {
                    d.resolve(result.data);
                    if (Object.keys(Attendees.rollCall.meetScheduleRules).length < 1 && result.data && result.data[0]) {
                      result.data.forEach( assembly => {
                        assembly.items.forEach( meet => {
                          Attendees.rollCall.meetScheduleRules[meet.slug] = {meetStart: meet.start, meetFinish: meet.finish, rules: meet.schedule_rules, assembly: meet.assembly};
                          Attendees.rollCall.meetData[meet.id] = [meet.finish, meet.major_character];  // cache the every meet's major characters for later use
                        })
                      });
                    }
                    const selectedMeetSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'selectedMeetSlugs') || [];
                    if (selectedMeetSlugs && selectedMeetSlugs[0]) {
                      Attendees.rollCall.filtersForm.getEditor('meets').option('value', selectedMeetSlugs[0]);
                    }
                  });
                return d.promise();
              },
              byKey: (key) => {
                // Somehow dxSelectBox needs byKey
              },
            }),
            key: 'slug',
          }),
        },
      },
      {
        colSpan: 12,
        dataField: "filtered_attendance_set",
        label: {
          location: 'top',
          text: ' ',  // empty space required for removing label
          showColon: false,
        },
        template: (data, itemElement) => {
          Attendees.rollCall.attendancesDatagrid = Attendees.rollCall.initFilteredattendancesDatagrid(data, itemElement);
        },
      },
    ],
  },

  initFilteredattendancesDatagrid: (data, itemElement) => {
    const $attendanceDatagrid = $("<div id='attendances-datagrid-container'>").dxDataGrid(Attendees.rollCall.attendanceDatagridConfig);
    itemElement.append($attendanceDatagrid);
    return $attendanceDatagrid.dxDataGrid('instance');
  },

  attendanceDatagridConfig: {
    dataSource: {
      store: new DevExpress.data.CustomStore({
        key: 'id',
        load: (loadOptions) => {
          Attendees.rollCall.loadOptions = loadOptions;
          const deferred = $.Deferred();
          const meet = Attendees.rollCall.filtersForm.getEditor('meets').option('value');
          const args = {
            start: new Date(new Date().setHours(new Date().getHours() - 1)).toISOString(),
            finish: new Date(new Date().setDate(new Date().getDate() + 5)).toISOString(),
          };
          if (meet) {
            args['meets'] = [meet];
          }

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
            url: $('form.filters-dxform').data('attendances-endpoint'),
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
              deferred.reject("Data Loading Error for attendances datagrid, probably time out?");
            },
            timeout: 60000,
          });
          return deferred.promise();
        },
        byKey: (key) => {
          const d = new $.Deferred();
          $.get($('form.filters-dxform').data('attendances-endpoint') + key + '/')
            .done((result) => {
              d.resolve(result.data);
            });
          return d.promise();
        },
        update: (key, values) => {
          return $.ajax({
            url: $('form.filters-dxform').data('attendances-endpoint') + key + '/',
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
        insert: (values) => {
          return $.ajax({
            url: $('form.filters-dxform').data('attendances-endpoint'),
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
            url: $('form.filters-dxform').data('attendances-endpoint') + key ,
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
    searchPanel: {
      visible: true,
      width: 240,
      placeholder: 'search name or activities ...',
    },
    allowColumnReordering: true,
    columnAutoWidth: true,
    allowColumnResizing: true,
    columnResizingMode: 'nextColumn',
    // cellHintEnabled: true,
    hoverStateEnabled: true,
    rowAlternationEnabled: true,
    remoteOperations: {groupPaging: true},
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
      type: 'sessionStorage',
      storageKey: Attendees.utilities.datagridStorageKeys['rollCallListView'],
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
    },
    columnChooser: {
      enabled: true,
      mode: 'select',
    },
    onToolbarPreparing: (e) => {
      const toolbarItems = e.toolbarOptions.items;
      toolbarItems.unshift({
        location: 'after',
        widget: 'dxButton',
        options: {
          hint: 'Reset Sort/Group/Columns/Meets settings',
          icon: 'pulldown',
          onClick() {
            if(confirm('Are you sure to reset all settings (Sort/Group/Columns/Meets) in this page?')) {
              Attendees.rollCall.attendancesDatagrid.state(null);
              window.sessionStorage.removeItem('rollCallListViewOpts');
              Attendees.utilities.selectAllGroupedTags(Attendees.rollCall.filtersForm.getEditor('meets'), []);
            }
          },
        },
      });
    },
    editing: {
      allowUpdating: false,
      allowAdding: false,
      allowDeleting: false,
      texts: {
        confirmDeleteMessage: 'Are you sure to delete it and all its future attendances? Instead, setting the "finish" date is usually enough!',
      },
      mode: 'popup',
      popup: {
        showTitle: true,
        title: 'attendanceEditingArgs',
        onContentReady: e => e.component.option('toolbarItems[0].visible', false),  // assembly
      },
      form: {
        colCount: 2,
        items: [
//          {
//            dataField: 'gathering',
//            helpText: "What's the activity?",
//          },
          {
            dataField: 'attending',
            helpText: "who?",
          },
//          {
//            dataField: 'character',
//            helpText: 'define participation role',
//          },
          {
            dataField: 'team',
            helpText: '(Optional) joining team',
          },
          {
            dataField: 'category',
            helpText: 'What type of participation?',
          },
//          {
//            dataField: 'infos.note',
//            helpText: 'special memo',
//            editorOptions: {
//              autoResizeEnabled: true,
//            },
//          },
//          {
//            dataField: 'start',
//            helpText: 'participation start time in browser timezone',
//          },
//          {
//            dataField: 'finish',
//            helpText: 'participation end time in browser timezone',
//          },
//          {
//            dataField: 'create_attendances_till',
//            disabled: true,
//            helpText: 'Auto create future attendances (not supported yet)',
//          },
        ],
      },
    },
    onCellClick: (e) => {
      if (e.rowType === 'data' && e.column.dataField === 'attending') {
        e.component.editRow(e.row.rowIndex);
      }
    },
    onInitNewRow: (e) => {
      e.data.start = new Date();
      Attendees.rollCall.attendancesDatagrid.option('editing.popup.title', 'Adding Attendance');
    },
    onEditingStart: (e) => {
      const grid = e.component;
      grid.beginUpdate();

      if (e.data && typeof e.data === 'object') {
        const title = Attendees.utilities.editingEnabled ? 'Editing Attendance' : 'Read only Info, please enable editing for modifications';
        grid.option('editing.popup.title', title);
      }
      grid.option("columns").forEach((column) => {
        grid.columnOption(column.dataField, "allowEditing", Attendees.utilities.editingEnabled);
      });
      grid.endUpdate();
    },
    columns: [
      {
        dataField: 'attending',
        validationRules: [{type: 'required'}],
        calculateDisplayValue: 'attending_name',  // can't use function when remoteOperations https://supportcenter.devexpress.com/ticket/details/t897726
        cellTemplate: (cellElement, cellInfo) => {
          cellElement.append ('<u role="button"><strong>' + cellInfo.displayValue + '</strong></u>');
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'attending_label',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: (loadOptions) => {
                const deferred = $.Deferred();
                const meet = Attendees.rollCall.filtersForm.getEditor('meets').option('value');
                loadOptions['sort'] = Attendees.rollCall.attendancesDatagrid && Attendees.rollCall.attendancesDatagrid.getDataSource().loadOptions().group;
                const args = {
                  // meets: $('div.selected-meets select').val(),
//                  characters: $('div.selected-characters select').val(),
                  searchOperation: loadOptions['searchOperation'],
                  searchValue: loadOptions['searchValue'],
                  searchExpr: loadOptions['searchExpr'],
                  start: new Date(new Date().setHours(new Date().getHours() - 1)).toISOString(),
                  finish: new Date(new Date().setDate(new Date().getDate() + 5)).toISOString(),
                };

                if (meet) {
                  args['meets'] = [meet];
                }

                [
                  'skip',
                  'take',
                  'requireTotalCount',
                  'requireGroupCount',
                  'sort',
                  'filter',
                  'totalSummary',
                  // 'group',
                  // 'groupSummary',
                ].forEach((i) => {
                  if (i in loadOptions && Attendees.utilities.isNotEmpty(loadOptions[i]))
                    args[i] = JSON.stringify(loadOptions[i]);
                });

                $.ajax({
                  url: $('form.filters-dxform').data('attendings-endpoint'),
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
                    deferred.reject("Data Loading Error for attending lookup, probably time out?");
                  },
                  timeout: 10000,
                });

                return deferred.promise();
              },
              byKey: (key) => {
                if (key) {
                  const d = $.Deferred();
                  $.get($('form.filters-dxform').data('attendings-endpoint') + key + '/').done((response) => {
                    d.resolve(response);
                  });
                  return d.promise();
                }
              },
            }),
          },
        },
      },
//      {
//        dataField: 'gathering',
//        validationRules: [{type: 'required'}],
//        caption: 'Gathering in Meet',
//        calculateDisplayValue: 'gathering_name',  // can't use function for remote operations https://supportcenter.devexpress.com/ticket/details/t897726
//        lookup: {
//          valueExpr: 'id',
//          displayExpr: 'display_name',
//          dataSource: (options) => {
//            return {
//              // filter: options.data ? {'meets[]': [options.data.meet]} : null,
//              store: new DevExpress.data.CustomStore({
//                key: 'id',
//                load: (searchOpts) => {
//                  if (options.data && options.data.meet) {
//                    searchOpts['meets[]'] = options.data.meet;
//                  } else {
//                    searchOpts['meets[]'] = $('div.selected-meets select').val();
//                  }
//                  return $.getJSON($('form.filters-dxform').data('gatherings-endpoint'), searchOpts);
//                },
//                byKey: (key) => {
//                  const d = new $.Deferred();
//                  $.get($('form.filters-dxform').data('gatherings-endpoint') + key + '/')
//                    .done((result) => {
//                      d.resolve(result);
//                    });
//                  return d.promise();
//                },
//              }),
//            };
//          }
//        },
//      },
//      {
//        dataField: 'gathering__meet__assembly',
//        groupIndex: 0,
//        validationRules: [{type: 'required'}],
//        caption: 'Group (Assembly)',
//        setCellValue: (newData, value, currentData) => {
//          newData.assembly = value;
//          newData.meet = null;
//          newData.character = null;
//          newData.team = null;
//        },
//        lookup: {
//          valueExpr: 'id',
//          displayExpr: 'display_name',
//          dataSource: {
//            store: new DevExpress.data.CustomStore({
//              key: 'id',
//              load: () => $.getJSON($('form.filters-dxform').data('assemblies-endpoint')),
//              byKey: (key) => {
//                if (key) {
//                  const d = $.Deferred();
//                  $.get($('form.filters-dxform').data('assemblies-endpoint') + key + '/').done((response) => {
//                    d.resolve(response);
//                  });
//                  return d.promise();
//                }
//              },
//            }),
//          },
//        },
//      },
//      {
//        dataField: 'character',
//        validationRules: [{type: 'required'}],
//        lookup: {
//          valueExpr: 'id',
//          displayExpr: 'display_name',
//          dataSource: (options) => {
//            return {
//              // filter: options.data ? {'assemblies[]': options.data.gathering__meet__assembly} : null,
//              store: new DevExpress.data.CustomStore({
//                key: 'id',
//                load: (searchOpts) => {
//                  searchOpts['take'] = 9999;
//                  if (options.data && options.data.gathering__meet__assembly) {
//                    searchOpts['assemblies[]'] = options.data.gathering__meet__assembly;
//                  } else {
//                    const meets = $('div.selected-meets select').val() || Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'selectedMeetSlugs');
//                    const assemblies = meets && meets.reduce((all, now) => {const meet = Attendees.rollCall.meetScheduleRules[now]; if(meet){all.add(meet.assembly)}; return all}, new Set());
//                    if (assemblies && assemblies.size){
//                      searchOpts['assemblies[]'] = Array.from(assemblies);
//                    }
//                  }
//                  return $.getJSON($('form.filters-dxform').data('characters-endpoint'), searchOpts);
//                },
//                byKey: (key) => {
//                  const d = new $.Deferred();
//                  $.get($('form.filters-dxform').data('characters-endpoint') + key + '/')
//                    .done((result) => {
//                      d.resolve(result);
//                    });
//                  return d.promise();
//                },
//              }),
//            };
//          }
//        },
//      },
      {
        dataField: 'category',
        validationRules: [{type: 'required'}],
        visible: false,
        editorOptions: {
          showClearButton: true,
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: (options) => {
            return {
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  searchOpts['type'] = 'attendance';
                  searchOpts['take'] = 9999;
                  return $.getJSON($('form.filters-dxform').data('categories-endpoint'), searchOpts);
                },
                byKey: (key) => {
                  const d = new $.Deferred();
                  $.get($('form.filters-dxform').data('categories-endpoint') + key + '/')
                    .done((result) => {
                      d.resolve(result);
                    });
                  return d.promise();
                },
              }),
            };
          }
        },
      },
      {
        dataField: 'team',
        visible: false,
        editorOptions: {
          showClearButton: true,
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: (options) => {
            return {
              // filter: options.data ? {gathering: options.data.gathering} : null,
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  searchOpts['take'] = 9999;
                  if (options.data && options.data.gathering) {  // for popup editor drop down limiting by chosen meet
                    searchOpts['gathering'] = options.data.gathering;
                  } else {  // for datagrid column lookup limiting by meet
                    const meet = Attendees.rollCall.filtersForm.getEditor('meets').option('value');
                    // const meetSlugs = $('div.selected-meets select').val();
                    const meets = meet ? [meet] : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['rollCallListViewOpts'], 'selectedMeetSlugs');
                    if (meets && meets.length) {
                      searchOpts['meets[]'] = meets;
                    }
                  }
                  return $.getJSON($('form.filters-dxform').data('teams-endpoint'), searchOpts);
                },
                byKey: (key) => {
                  const d = new $.Deferred();
                  $.get($('form.filters-dxform').data('teams-endpoint') + key + '/')
                    .done((result) => {
                      d.resolve(result);
                    });
                  return d.promise();
                },
              }),
            };
          }
        },
      },
//      {
//        dataField: 'create_attendances_till',
//        visible: false,
//        dataType: 'datetime',
//        label: {
//          text: 'Reserve attendances to',
//        },
//        editorOptions: {
//          type: 'datetime',
//          showClearButton: true,
//          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
//        }
//      },
//      {
//        dataField: 'start',
//        dataType: 'datetime',
//        format: 'MM/dd/yyyy',
//        editorOptions: {
//          type: 'datetime',
//          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
//        },
//      },
//      {
//        dataField: 'finish',
//        dataType: 'datetime',
//        format: 'MM/dd/yyyy',
//        editorOptions: {
//          type: 'datetime',
//          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
//        },
//      },
//      {
//        dataField: 'infos.note',
//        caption: 'Note',
//        dataType: 'string',
//      },
    ],
  },
};

$(document).ready(() => {
  Attendees.rollCall.init();
});
