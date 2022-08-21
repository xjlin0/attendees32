Attendees.attendances = {
  filtersForm: null,
  meetScheduleRules: {},
  selectedMeetHasRule: false,
  initialized: false,
  filterMeetCheckbox: null,
  loadOptions: null,
  selectedCharacterSlugs: [],
  selectedMeetSlugs: [],
  meetData: {},
  gatheringMeet: {},
  init: () => {
    console.log('static/js/occasions/attendances_list_view.js');
    Attendees.utilities.clearGridStatesInSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListView']); // remove saved search text without interfering column visibility
    Attendees.attendances.initFilterMeetCheckbox();
    Attendees.attendances.initEditingSwitch();
    Attendees.attendances.initFiltersForm();
    Attendees.attendances.initGenerateButton();
  },

  initEditingSwitch: () => {
    const $editSwitcherDiv = $('div#custom-control-edit-switch');
    if ($editSwitcherDiv && $editSwitcherDiv.length){
      $editSwitcherDiv.dxSwitch({
        value: Attendees.utilities.editingEnabled,
        switchedOffText: 'Editing disabled',
        switchedOnText: 'Editing enabled',
        hint: 'Toggle Editing mode',
        width: '18%',
        height: '110%',
        onValueChanged: (e) => {  // not reconfirm, it's already after change
          Attendees.utilities.editingEnabled = e.value;
          Attendees.attendances.toggleEditing(e.value);
        },
      })
    }
  },

  initFilterMeetCheckbox: () => {
    Attendees.attendances.filterMeetCheckbox = $('div#custom-control-filter-meets-checkbox').dxCheckBox({
      value: true,
      hint: 'When checked, the dropdown list of Meets will be filtered based on the From/Till date&time',
      text: 'Filter meets by date/time',
      onValueChanged: (e) => {
        Attendees.attendances.filtersForm.getEditor('meets').getDataSource().reload();
      }
    }).dxCheckBox('instance');
  },

  initGenerateButton: () => {  // it doesn't need characters but still check so user won't generate repeating attendances
    const generateAttendancesButtonDiv = document.querySelector('div#generate-attendances');
    if (generateAttendancesButtonDiv) {
      Attendees.attendances.generateGatheringsButton = $('div#generate-attendances').dxButton({
        disabled: true,
        text: 'Generate Attendances',
        height: '1.5rem',
        hint: 'Generate attendances based on attendingmeet. Disabled when multiple meets selected or "Till" empty',
        onClick: () => {
          const filterTill = $('div.filter-till input')[1].value;
          if (filterTill && confirm('Are you sure to auto generate all attendances of the chosen meet before the filtered date from character defined in the enrollment?')) {
            const params = {};
            const filterFrom = $('div.filter-from input')[1].value;
            params['begin'] = filterFrom ? new Date(filterFrom).toISOString() : new Date().toISOString();
            params['end'] = filterTill ? new Date(filterTill).toISOString() : null;
            const meetSlugs = $('div.selected-meets select').val();
            if (params['end'] && Attendees.attendances.filtersForm.validate().isValid && meetSlugs.length && meetSlugs.length === 1) {
              params['meet_slug'] = meetSlugs[0];
              return $.ajax({
                url: $('form.filters-dxform').data('series-attendances-endpoint'),
                method: 'POST',
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
                data: JSON.stringify(params),
                success: (result) => {
                  DevExpress.ui.notify(
                    {
                      message: 'Batch processed, ' + result.number_created + ' successfully created between ' + new Date(result.begin).toLocaleString() + ' & ' + new Date(result.end).toLocaleString(),
                      width: 500,
                      position: {
                        my: 'center',
                        at: 'center',
                        of: window,
                      },
                    }, 'success', 3000);
                },
                error: (result) => {
                  console.log("hi gatherings_list_view.js 87 here is error result: ", result);
                  DevExpress.ui.notify(
                    {
                      message: 'Batch processing error. ' + result && result.responseText,
                      width: 500,
                      position: {
                        my: 'center',
                        at: 'center',
                        of: window,
                      },
                    }, 'error', 5000);
                },
                complete: () => {
                  Attendees.attendances.gatheringsDatagrid.refresh();
                }, // partial attendances may have generated even when errors
              });
            } else {
              DevExpress.ui.notify(
                {
                  message: "Can't generate, Please select one single meet with duration, and Filter 'till' earlier than filter 'from'",
                  width: 500,
                  position: {
                    my: 'center',
                    at: 'center',
                    of: window,
                  },
                }, 'error', 2000);
            }
          }
        },
      }).dxButton('instance');
    }
  },

  toggleEditing: (enabled) => {
    if (Attendees.attendances.attendancesDatagrid) {
      Attendees.attendances.attendancesDatagrid.option('editing.allowUpdating', enabled);
      Attendees.attendances.attendancesDatagrid.option('editing.allowAdding', enabled);
      Attendees.attendances.attendancesDatagrid.option('editing.allowDeleting', enabled);
      Attendees.attendances.attendancesDatagrid.option('editing.popup.onContentReady', e => e.component.option('toolbarItems[0].visible', enabled));
    }
    Attendees.attendances.generateGatheringsButton.option('disabled', !Attendees.attendances.readyToGenerate());
  },

  readyToGenerate: () => {
    const filterFrom = Attendees.attendances.filtersForm.getEditor('filter-from').option('value');
    const filterTill = Attendees.attendances.filtersForm.getEditor('filter-till').option('value');
    const selectedMeet = Attendees.attendances.filtersForm.getEditor('meets').option('value');
    const intervalValid = filterTill && (filterFrom ? filterTill > filterFrom : true);

    return Attendees.attendances.selectedMeetHasRule &&
      Attendees.attendances.filtersForm.validate().isValid &&
      intervalValid && selectedMeet && selectedMeet.length === 1
  },

  initFiltersForm: () => {
    $.ajaxSetup({
      headers: {
        'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
      }
    });
    Attendees.attendances.filtersForm = $('form.filters-dxform').dxForm(Attendees.attendances.filterFormConfigs).dxForm('instance');
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
        helpText: `mm/dd/yyyy in ${Intl.DateTimeFormat().resolvedOptions().timeZone} time`,
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
          value: Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterFromString') === undefined ? new Date(new Date().setHours(new Date().getHours() - 1)) : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterFromString') ? Date.parse(Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterFromString')) : null,
          type: 'datetime',
          onValueChanged: (e) => {
            const filterFromString = e.value ? e.value.toJSON() : null;  // it can be null to get all rows
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterFromString', filterFromString);
            if (Attendees.attendances.filterMeetCheckbox.option('value')) {
              Attendees.attendances.filtersForm.getEditor('meets').getDataSource().reload();
            }
            const meets = $('div.selected-meets select').val();
            const characters = $('div.selected-characters select').val();
            if (meets.length && characters.length) {
              Attendees.attendances.attendancesDatagrid.refresh();
            }
          },
        },
      },
      {
        colSpan: 3,
        cssClass: 'filter-till',
        dataField: 'filter-till',
        helpText: `mm/dd/yyyy in ${Intl.DateTimeFormat().resolvedOptions().timeZone} time`,
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
          value: Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterTillString') === undefined ? new Date(new Date().setMonth(new Date().getMonth() + 1)) : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterTillString') ? Date.parse(Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterTillString')) : null,
          type: 'datetime',
          onValueChanged: (e) => {
            Attendees.attendances.generateGatheringsButton.option('disabled', !Attendees.attendances.readyToGenerate());
            const filterTillString = e.value ? e.value.toJSON() : null;  // it can be null to get all rows
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterTillString', filterTillString);
            if (Attendees.attendances.filterMeetCheckbox.option('value')) {
              Attendees.attendances.filtersForm.getEditor('meets').getDataSource().reload();
            }  // allow users to screen only active meets by meet's start&finish
            const meets = $('div.selected-meets select').val();
            const characters = $('div.selected-characters select').val();
            if (meets.length && characters.length) {
              Attendees.attendances.attendancesDatagrid.refresh();
            }
          },
        },
      },
      {
        dataField: 'meets',
        colSpan: 6,
        helpText: "Can't show schedules when multiple selected. Select single one to view its schedules. Please notice that certain ones have NO attendances purposely",
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
                  Attendees.utilities.selectAllGroupedTags(Attendees.attendances.filtersForm.getEditor('meets'));
                },
              },
            }
          ],
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
          onValueChanged: (e)=> {
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'selectedMeetSlugs', e.value);
            Attendees.attendances.filtersForm.validate();
            const defaultHelpText = "Can't show schedules when multiple selected. Select single one to view its schedules. Please notice that certain ones have NO attendances purposely";
            const $meetHelpText = Attendees.attendances.filtersForm.getEditor('meets').element().parent().parent().find(".dx-field-item-help-text");
            Attendees.attendances.selectedMeetHasRule = false;
            // Attendees.attendances.generateGatheringsButton.option('disabled', true);
            $meetHelpText.text(defaultHelpText);  // https://supportcenter.devexpress.com/ticket/details/t531683
            if (e.value && e.value.length > 0) {
              if (Attendees.attendances.attendancesDatagrid.totalCount() > 0) {
                Attendees.attendances.filtersForm.getEditor('characters').option('value', []);
                Attendees.attendances.filtersForm.getEditor('characters').getDataSource().reload();
              }
              const characters = $('div.selected-characters select').val();
              if (characters.length) {
                Attendees.attendances.attendancesDatagrid.refresh();
              }
              if (e.value.length < 2) {
                const newHelpTexts = [];
                let finalHelpText = '';
                let lastDuration = 0;
                const noRuleText = 'This meet does not have schedules in EventRelation';
                const ruleData = Attendees.attendances.meetScheduleRules[ e.value[0] ];
                const timeRules = ruleData.rules;
                const meetStart = new Date(ruleData.meetStart).toDateString();
                const meetFinish = new Date(ruleData.meetFinish).toDateString();
                if (timeRules && timeRules.length > 0) {
                  timeRules.forEach(timeRule => {
                    if (timeRule.rule) {
                      Attendees.attendances.selectedMeetHasRule = true;
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
                  // if (Attendees.attendances.selectedMeetHasRule && $('div#custom-control-edit-switch').dxSwitch('instance').option('value') && lastDuration > 0) {
                  //   Attendees.attendances.generateGatheringsButton.option('disabled', false);
                  // }
                } else {
                  finalHelpText = noRuleText;
                }
                $meetHelpText.text(finalHelpText);  // https://supportcenter.devexpress.com/ticket/details/t531683
                // Attendees.attendances.filtersForm.itemOption('duration', {editorOptions: {value: lastDuration}});
              }
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {grouping: 'assembly_name', model: 'attendance'};  // for grouped: true,

                if (Attendees.attendances.filterMeetCheckbox.option('value')) {
                  const filterFrom = $('div.filter-from input')[1].value;
                  const filterTill = $('div.filter-till input')[1].value;
                  params['start'] = filterFrom ? new Date(filterFrom).toISOString() : null;
                  params['finish'] = filterTill ? new Date(filterTill).toISOString() : null;
                  // params['grouping'] = 'assembly_name';  // for grouped: true,
                }
                $.get($('form.filters-dxform').data('meets-endpoint-by-slug'), params)
                  .done((result) => {
                    d.resolve(result.data);
                    if (Object.keys(Attendees.attendances.meetScheduleRules).length < 1 && result.data && result.data[0]) {
                      result.data.forEach( assembly => {
                        assembly.items.forEach( meet => {
                          Attendees.attendances.meetScheduleRules[meet.slug] = {meetStart: meet.start, meetFinish: meet.finish, rules: meet.schedule_rules, assembly: meet.assembly};
                          Attendees.attendances.meetData[meet.id] = [meet.finish, meet.major_character];  // cache the every meet's major characters for later use
                        })
                      }); // schedule rules needed for attendingmeets generation
                    }
                    const selectedMeetSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'selectedMeetSlugs') || [];
                    Attendees.utilities.selectAllGroupedTags(Attendees.attendances.filtersForm.getEditor('meets'), selectedMeetSlugs);
                  });
                return d.promise();
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
                  Attendees.utilities.selectAllGroupedTags(Attendees.attendances.filtersForm.getEditor('characters'));
                },
              },
            }
          ],
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
          onValueChanged: (e)=> {
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'selectedCharacterSlugs', e.value);
            Attendees.attendances.filtersForm.validate();
            Attendees.attendances.generateGatheringsButton.option('disabled', !Attendees.attendances.readyToGenerate());
            const meets = $('div.selected-meets select').val();
            if (meets.length && e.value && e.value.length > 0 && Attendees.attendances.attendancesDatagrid) {
              Attendees.attendances.attendancesDatagrid.refresh();
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {take: 9999};
                const meetSlugs = $('div.selected-meets select').val();
                const meets = meetSlugs && meetSlugs.length ? meetSlugs : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'selectedMeetSlugs');
                const assemblies = meets && meets.reduce((all, now) => {const meet = Attendees.attendances.meetScheduleRules[now]; if(meet){all.add(meet.assembly)}; return all}, new Set());
                if (assemblies && assemblies.size){
                  params['assemblies[]'] = Array.from(assemblies);
                }
                if (Attendees.attendances.filterMeetCheckbox.option('value')) {
                  params['grouping'] = 'assembly_name';  // for grouped: true,
                }
                $.get($('form.filters-dxform').data('characters-endpoint'), params)
                  .done((result) => {
                    d.resolve(result.data);
                    const selectedCharacterSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'selectedCharacterSlugs') || [];
                    Attendees.utilities.selectAllGroupedTags(Attendees.attendances.filtersForm.getEditor('characters'), selectedCharacterSlugs);
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
        dataField: "filtered_attendance_set",
        label: {
          location: 'top',
          text: ' ',  // empty space required for removing label
          showColon: false,
        },
        template: (data, itemElement) => {
          Attendees.attendances.attendancesDatagrid = Attendees.attendances.initFilteredattendancesDatagrid(data, itemElement);
        },
      },
    ],
  },

  initFilteredattendancesDatagrid: (data, itemElement) => {
    const $attendanceDatagrid = $("<div id='attendances-datagrid-container'>").dxDataGrid(Attendees.attendances.attendanceDatagridConfig);
    itemElement.append($attendanceDatagrid);
    return $attendanceDatagrid.dxDataGrid('instance');
  },

  attendanceDatagridConfig: {
    dataSource: {
      store: new DevExpress.data.CustomStore({
        key: 'id',
        load: (loadOptions) => {
          Attendees.attendances.loadOptions = loadOptions;
          const meets = $('div.selected-meets select').val();
          const characters = $('div.selected-characters select').val();
          const deferred = $.Deferred();

          if (meets && meets.length > 0 && characters && characters.length > 0) {
            const args = {
              meets: meets,
              characters: characters,
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
              url: $('form.filters-dxform').data('attendances-endpoint'),
              dataType: "json",
              data: args,
              success: (result) => {
                deferred.resolve(result.data, {
                  totalCount: result.totalCount,
                  summary: result.summary,
                  groupCount: result.groupCount,
                });
              },
              error: () => {
                deferred.reject("Data Loading Error for attendances datagrid, probably time out?");
              },
              timeout: 60000,
            });
          } else {
            deferred.resolve([], {totalCount: 0, groupCount: 0});
          }
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
      storageKey: Attendees.utilities.datagridStorageKeys['attendancesListView'],
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
          hint: 'Reset Sort/Group/Columns/Meets/Character/Time settings',
          icon: 'clearsquare',
          onClick() {
            if(confirm('Are you sure to reset all settings (Sort/Group/Columns/Meets/Character/Time) in this page?')) {
              Attendees.attendances.attendancesDatagrid.state(null);
              window.sessionStorage.removeItem('attendancesListViewOpts');
              Attendees.utilities.selectAllGroupedTags(Attendees.attendances.filtersForm.getEditor('characters'), []);
              Attendees.utilities.selectAllGroupedTags(Attendees.attendances.filtersForm.getEditor('meets'), []);
              Attendees.attendances.filtersForm.getEditor('filter-from').option('value', new Date(new Date().setHours(new Date().getHours() - 1)));
              Attendees.attendances.filtersForm.getEditor('filter-till').option('value', new Date(new Date().setMonth(new Date().getMonth() + 1)));
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
          {
            dataField: 'gathering',
            helpText: "What's the activity?",
          },
          {
            dataField: 'attending',
            helpText: "who?",
          },
          {
            dataField: 'character',
            helpText: 'define participation role',
          },
          {
            dataField: 'team',
            helpText: '(Optional) joining team',
          },
          {
            dataField: 'category',
            helpText: 'What type of participation?',
          },
          {
            dataField: 'start',
            helpText: '(Optional)participation start time in browser timezone',
          },
          {
            dataField: 'finish',
            helpText: '(Optional)participation end time in browser timezone',
          },
//          {
//            dataField: 'create_attendances_till',
//            disabled: true,
//            helpText: '(Optional)Auto create future attendances (not supported yet)',
//          },
          {
            dataField: 'infos.note',
            helpText: '(Optional)special memo',
            editorType: 'dxTextArea',
//            colSpan: 2,
            editorOptions: {
              autoResizeEnabled: true,
            },
          },
        ],
      },
    },
    onCellClick: (e) => {
      if (e.rowType === 'data' && e.column.dataField === 'attending') {
        e.component.editRow(e.row.rowIndex);
      }
    },
    onInitNewRow: (e) => {
      e.data.category = 1;
      Attendees.attendances.attendancesDatagrid.option('editing.popup.title', 'Adding Attendance');
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
        calculateDisplayValue: 'attending__attendee__infos__names__original',  // can't use function when remoteOperations https://supportcenter.devexpress.com/ticket/details/t897726
        cellTemplate: (cellElement, cellInfo) => {
          cellElement.append ('<u role="button"><strong>' + cellInfo.displayValue + '</strong></u>');
        },
        placeholder: "Select or search...",
        editorOptions: {
           noDataText: "Nothing! Ever enrolled?",
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'attending_label',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: (loadOptions) => {
                const meets = $('div.selected-meets select').val();
                const characters = $('div.selected-characters select').val();
                const deferred = $.Deferred();
                loadOptions['sort'] = Attendees.attendances.attendancesDatagrid && Attendees.attendances.attendancesDatagrid.getDataSource().loadOptions().group;
                const args = {
                  meets: meets,
                  characters: characters,
                  searchOperation: loadOptions['searchOperation'],
                  searchValue: loadOptions['searchValue'],
                  searchExpr: loadOptions['searchExpr'],
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
      {
        dataField: 'gathering',
        validationRules: [{type: 'required'}],
        caption: 'Gathering in Meet',
        placeholder: "Select or search...",
        calculateDisplayValue: 'gathering__display_name',  // can't use function for remote operations https://supportcenter.devexpress.com/ticket/details/t897726
        setCellValue: (newData, value, currentData) => {
          if (value) {
            newData.gathering = value;
            const gatheringsMeet = Attendees.attendances.gatheringMeet[value];
            if (gatheringsMeet && !currentData.character) {
              const [meetEnd, majorCharacter] = Attendees.attendances.meetData[gatheringsMeet];
              newData.character = majorCharacter;
            }  // when no character's define, set default character for user.
          }
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'gathering_label',
          dataSource: (options) => {
            return {
              // filter: options.data ? {'meets[]': [options.data.meet]} : null,
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  if (options.data && options.data.meet) {
                    searchOpts['meets[]'] = options.data.meet;
                  } else {
                    searchOpts['meets[]'] = $('div.selected-meets select').val();
                  }
                  const d = new $.Deferred();
                  $.get($('form.filters-dxform').data('gatherings-endpoint'), searchOpts)
                    .done((result) => {
                      result && result.data && result.data.forEach( gathering => {
                        Attendees.attendances.gatheringMeet[gathering.id] = gathering.meet;
                      })
                      d.resolve(result);
                    });
                  return d.promise();
                },
                byKey: (key) => {
                  const d = new $.Deferred();
                  $.get($('form.filters-dxform').data('gatherings-endpoint') + key + '/')
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
        dataField: 'gathering__meet__assembly',
        groupIndex: 0,
        validationRules: [{type: 'required'}],
        caption: 'Group (Assembly)',
        setCellValue: (newData, value, currentData) => {
          newData.assembly = value;
          newData.meet = null;
          newData.character = null;
          newData.team = null;
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: () => $.getJSON($('form.filters-dxform').data('assemblies-endpoint')),
              byKey: (key) => {
                if (key) {
                  const d = $.Deferred();
                  $.get($('form.filters-dxform').data('assemblies-endpoint') + key + '/').done((response) => {
                    d.resolve(response);
                  });
                  return d.promise();
                }
              },
            }),
          },
        },
      },
      {
        dataField: 'gathering__meet',
        visible: false,
        validationRules: [{type: 'required'}],
        caption: 'Meet',
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: () => $.getJSON($('form.filters-dxform').data('meets-endpoint-by-id'), {take: 9999}),
              byKey: (key) => {
                if (key) {
                  const d = $.Deferred();
                  $.get($('form.filters-dxform').data('meets-endpoint-by-id') + key + '/').done((response) => {
                    d.resolve(response);
                  });
                  return d.promise();
                }
              },
            }),
          },
        },
      },
      {
        dataField: 'character',
        validationRules: [{type: 'required'}],
        setCellValue: (newData, value, currentData) => {
          if (value) {
            newData.character = value;
          }  // for preventing gathering default character overwriting
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: (options) => {
            return {
              // filter: options.data ? {'assemblies[]': options.data.gathering__meet__assembly} : null,
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  searchOpts['take'] = 9999;
                  if (options.data && options.data.gathering__meet__assembly) {
                    searchOpts['assemblies[]'] = options.data.gathering__meet__assembly;
                  } else {
                    const meets = $('div.selected-meets select').val() || Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'selectedMeetSlugs');
                    const assemblies = meets && meets.reduce((all, now) => {const meet = Attendees.attendances.meetScheduleRules[now]; if(meet){all.add(meet.assembly)}; return all}, new Set());
                    if (assemblies && assemblies.size){
                      searchOpts['assemblies[]'] = Array.from(assemblies);
                    }
                  }
                  return $.getJSON($('form.filters-dxform').data('characters-endpoint'), searchOpts);
                },
                byKey: (key) => {
                  const d = new $.Deferred();
                  $.get($('form.filters-dxform').data('characters-endpoint') + key + '/')
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
                    const meetSlugs = $('div.selected-meets select').val();
                    const meets = meetSlugs && meetSlugs.length ? meetSlugs : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'selectedMeetSlugs');
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
      {
        dataField: 'start',
        visible: false,
        dataType: 'datetime',
        format: 'MM/dd/yyyy',
        editorOptions: {
          type: 'datetime',
          showClearButton: true,
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        },
      },
      {
        dataField: 'finish',
        visible: false,
        dataType: 'datetime',
        format: 'MM/dd/yyyy',
        editorOptions: {
          type: 'datetime',
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        },
      },
      {
        dataField: 'infos.note',
        allowGrouping: false,
        caption: 'Note',
        dataType: 'string',
      },
    ],
  },
};

$(document).ready(() => {
  Attendees.attendances.init();
});
