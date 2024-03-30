Attendees.attendanceStatistics = {
  filtersForm: null,
  meetScheduleRules: {},
  selectedMeetHasRule: false,
  allowEditingAttending: false,
  filterMeetCheckbox: null,
  selectedCharacterSlugs: [],
  selectedMeetSlugs: [],
  meetData: {},
  gatheringMeet: {},
  init: () => {
    console.log('static/js/occasions/attendance_statistics_list_view.js');
    Attendees.utilities.clearGridStatesInSessionStorage(Attendees.utilities.datagridStorageKeys['attendanceStatisticsListView']); // remove saved search text without interfering column visibility
    Attendees.attendanceStatistics.initFilterMeetCheckbox();
    Attendees.attendanceStatistics.initFiltersForm();
  },

  updateGatheringCountAndDatagrid: () => {
    const d = new $.Deferred();
    const filterFrom = Attendees.attendanceStatistics.filtersForm.getEditor('filter-from').option('value');
    const filterTill = Attendees.attendanceStatistics.filtersForm.getEditor('filter-till').option('value');
    const meets = Attendees.attendanceStatistics.filtersForm.getEditor('meets').option('value');

    if (Array.isArray(meets) && meets.length) {
      const params = {
        take: 9999,
        meets: meets,
        start: filterFrom.toISOString(),
        finish: filterTill.toISOString(),
      };

      $.get($('form.filters-dxform').data('gatherings-endpoint'), params)
        .done((result) => {
          const gatheringCounter = document.querySelector('span#gathering-count');
          if (gatheringCounter) {
            gatheringCounter.textContent = result.totalCount;
          }
          Attendees.attendanceStatistics.attendancesDatagrid.refresh();
          d.resolve(result.data);
        });
    }
  },

  initFilterMeetCheckbox: () => {
    Attendees.attendanceStatistics.filterMeetCheckbox = $('div#custom-control-filter-meets-checkbox').dxCheckBox({
      value: true,
      hint: 'When checked, the dropdown list of Meets will be filtered based on the From/Till date&time',
      text: 'Filter meets by date/time',
      onValueChanged: (e) => {
        Attendees.attendanceStatistics.filtersForm.getEditor('meets').getDataSource().reload();
      }
    }).dxCheckBox('instance');
  },

  initFiltersForm: () => {
    $.ajaxSetup({
      headers: {
        'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
      }
    });
    Attendees.attendanceStatistics.filtersForm = $('form.filters-dxform').dxForm(Attendees.attendanceStatistics.filterFormConfigs).dxForm('instance');
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
        helpText: `Gathering from mm/dd/yyyy in ${Intl.DateTimeFormat().resolvedOptions().timeZone} time`,
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
          value: new Date(
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterFromString') ?
              Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterFromString') :
              new Date().setHours(new Date().getHours() - 1)
          ),
          type: 'datetime',
          onValueChanged: (e) => {
            const filterFromString = e.value ? e.value.toJSON() : null;  // it can be null to get all rows
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterFromString', filterFromString);
            if (Attendees.attendanceStatistics.filterMeetCheckbox.option('value')) {
              Attendees.attendanceStatistics.filtersForm.getEditor('meets').getDataSource().reload();
            }
            const meets = $('div.selected-meets select').val();
            const characters = $('div.selected-characters select').val();
            if (meets.length && characters.length) {
              Attendees.attendanceStatistics.updateGatheringCountAndDatagrid();
            }
          },
        },
      },
      {
        colSpan: 3,
        cssClass: 'filter-till',
        dataField: 'filter-till',
        helpText: `Gathering till mm/dd/yyyy in ${Intl.DateTimeFormat().resolvedOptions().timeZone} time`,
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
          text: 'Till(excluded)',
        },
        editorType: 'dxDateBox',
        editorOptions: {
          showClearButton: true,
          type: 'datetime',
          value: new Date(
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendanceStatisticsListViewOpts'], 'filterTillString') ?
              Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendanceStatisticsListViewOpts'], 'filterTillString') :
              new Date().setMonth(new Date().getMonth() + 1)
          ),
          onValueChanged: (e) => {
            const filterTillString = e.value ? e.value.toJSON() : null;  // it can be null to get all rows
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendancesListViewOpts'], 'filterTillString', filterTillString);
            if (Attendees.attendanceStatistics.filterMeetCheckbox.option('value')) {
              Attendees.attendanceStatistics.filtersForm.getEditor('meets').getDataSource().reload();
            }  // allow users to screen only active meets by meet's start&finish
            const meets = $('div.selected-meets select').val();
            const characters = $('div.selected-characters select').val();
            if (meets.length && characters.length) {
              Attendees.attendanceStatistics.updateGatheringCountAndDatagrid();
            }
          },
        },
      },
      {
        dataField: 'meets',
        colSpan: 4,
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
                  Attendees.utilities.selectAllGroupedTags(Attendees.attendanceStatistics.filtersForm.getEditor('meets'));
                },
              },
            }
          ],
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
          onValueChanged: (e)=> {
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendanceStatisticsListViewOpts'], 'selectedMeetSlugs', e.value);
            Attendees.attendanceStatistics.filtersForm.validate();
            const defaultHelpText = "Can't show schedules when multiple selected. Select single one to view its schedules. Please notice that certain ones have NO attendances purposely";
            const $meetHelpText = Attendees.attendanceStatistics.filtersForm.getEditor('meets').element().parent().parent().find(".dx-field-item-help-text");
            Attendees.attendanceStatistics.selectedMeetHasRule = 0;
            $meetHelpText.text(defaultHelpText);  // don't use itemOption!! https://supportcenter.devexpress.com/ticket/details/t531683
            if (e.value && e.value.length > 0) {
              Attendees.attendanceStatistics.filtersForm.getEditor('characters').option('value', []);
              Attendees.attendanceStatistics.filtersForm.getEditor('characters').getDataSource().reload();
              const categories = $('div.selected-categories select').val();
              if (categories && categories.length) {
                Attendees.attendanceStatistics.updateGatheringCountAndDatagrid();
              }
              if (e.value.length < 2) {
                const newHelpTexts = [];
                let finalHelpText = '';
                let lastDuration = 0;
                const noRuleText = 'This meet does not have schedules in EventRelation';
                const ruleData = Attendees.attendanceStatistics.meetScheduleRules[ e.value[0] ];
                const timeRules = ruleData.rules;
                const meetStart = new Date(ruleData.meetStart).toDateString();
                const meetFinish = new Date(ruleData.meetFinish).toDateString();
                if (timeRules && timeRules.length > 0) {
                  timeRules.forEach(timeRule => {
                    if (timeRule.rule) {
                      Attendees.attendanceStatistics.selectedMeetHasRule = timeRules.length;
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
                Attendees.attendanceStatistics.filtersForm.updateData("duration", lastDuration);  // don't use itemOption!! https://supportcenter.devexpress.com/ticket/details/t531683
                $meetHelpText.text(finalHelpText);  // don't use itemOption!! https://supportcenter.devexpress.com/ticket/details/t531683
              }
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {take: 999, grouping: 'assembly_name', model: 'attendance'};  // for grouped: true,

                if (Attendees.attendanceStatistics.filterMeetCheckbox.option('value')) {
                  const filterFrom = $('div.filter-from input')[1].value;
                  const filterTill = $('div.filter-till input')[1].value;
                  params['start'] = filterFrom ? new Date(filterFrom).toISOString() : null;
                  params['finish'] = filterTill ? new Date(filterTill).toISOString() : null;
                  // params['grouping'] = 'assembly_name';  // for grouped: true,
                }
                $.get($('form.filters-dxform').data('meets-endpoint-by-slug'), params)
                  .done((result) => {
                    d.resolve(result.data);
                    if (Object.keys(Attendees.attendanceStatistics.meetScheduleRules).length < 1 && result.data && result.data[0]) {
                      result.data.forEach( assembly => {
                        assembly.items.forEach( meet => {
                          Attendees.attendanceStatistics.meetScheduleRules[meet.slug] = {meetStart: meet.start, meetFinish: meet.finish, rules: meet.schedule_rules, assembly: meet.assembly};
                          Attendees.attendanceStatistics.meetData[meet.id] = [meet.finish, meet.major_character];  // cache the every meet's major characters for later use
                        })
                      }); // schedule rules needed for display
                    }
                    const selectedMeetSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendanceStatisticsListViewOpts'], 'selectedMeetSlugs') || [];
                    Attendees.utilities.selectAllGroupedTags(Attendees.attendanceStatistics.filtersForm.getEditor('meets'), selectedMeetSlugs);
                  });
                return d.promise();
              },
            }),
            key: 'slug',
          }),
        },
      },
      {
        colSpan: 2,
        dataField: 'categories',
        cssClass: 'selected-categories',
        editorType: 'dxTagBox',
        validationRules: [{type: 'required'}],
        helpText: '(to be counted)',
        label: {
          location: 'top',
          text: 'category',
        },
        editorOptions: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          value: [9],
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: (searchOpts) => {
                const d = new $.Deferred();
                searchOpts['type'] = 'attendance';
                searchOpts['take'] = 9999;
                $.get($('form.filters-dxform').data('categories-endpoint'), searchOpts)
                  .done((result) => {
                    d.resolve(result.data);
                  });
                return d.promise();
              },
            }),
            key: 'id',
          }),
          onValueChanged: (e)=> {
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendanceStatisticsListViewOpts'], 'selectedCategoryIds', e.value);
            Attendees.attendanceStatistics.filtersForm.validate();
            const meets = $('div.selected-meets select').val();
            if (meets.length && e.value && e.value.length > 0 && Attendees.attendanceStatistics.attendancesDatagrid) {
              Attendees.attendanceStatistics.updateGatheringCountAndDatagrid();
            }
          },
        },
      },
      {
        dataField: 'characters',
        colSpan: 8,
//        helpText: 'Select one or more characters to filter results',
        cssClass: 'selected-characters',
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
                  Attendees.utilities.selectAllGroupedTags(Attendees.attendanceStatistics.filtersForm.getEditor('characters'));
                },
              },
            }
          ],
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
          onValueChanged: (e)=> {
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendanceStatisticsListViewOpts'], 'selectedCharacterSlugs', e.value);
            Attendees.attendanceStatistics.filtersForm.validate();
            const meets = $('div.selected-meets select').val();
            const categories = $('div.selected-categories select').val();
            if (!Attendees.utilities.areTwoArraysTheSame(e.value, e.previousValue) &&  meets && meets.length && categories && categories.length && Attendees.attendanceStatistics.attendancesDatagrid) {
              Attendees.attendanceStatistics.updateGatheringCountAndDatagrid();
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {take: 9999, grouping: 'assembly_name'};  // for grouped: true,
                const meetSlugs = $('div.selected-meets select').val();
                const meets = meetSlugs && meetSlugs.length ? meetSlugs : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendanceStatisticsListViewOpts'], 'selectedMeetSlugs');
                const assemblies = meets && meets.reduce((all, now) => {const meet = Attendees.attendanceStatistics.meetScheduleRules[now]; if(meet){all.add(meet.assembly)}; return all}, new Set());
                if (assemblies && assemblies.size){
                  params['assemblies[]'] = Array.from(assemblies);
                }
                $.get($('form.filters-dxform').data('characters-endpoint'), params)
                  .done((result) => {
                    d.resolve(result.data);
                    const selectedCharacterSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendanceStatisticsListViewOpts'], 'selectedCharacterSlugs') || [];
                    Attendees.utilities.selectAllGroupedTags(Attendees.attendanceStatistics.filtersForm.getEditor('characters'), selectedCharacterSlugs);
                  });
                return d.promise();
              },
            }),
            key: 'slug',
          }),
        },
      },
      {
        colSpan: 4,
        dataField: 'teams',
        cssClass: 'selected-teams',
        editorType: 'dxTagBox',
//        helpText: 'Select one or more teams to filter results',
        label: {
          location: 'top',
          text: 'Select teams',
        },
        editorOptions: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          showClearButton: true,
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: (searchOpts) => {
                  searchOpts['take'] = 9999;
                    const meetSlugs = $('div.selected-meets select').val();
                    const meets = meetSlugs && meetSlugs.length ? meetSlugs : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendanceStatisticsListViewOpts'], 'selectedMeetSlugs');
                    if (meets && meets.length) {
                      searchOpts['meets[]'] = meets;
                    }
                  return $.getJSON($('form.filters-dxform').data('teams-endpoint'), searchOpts);
              },
            }),
            key: 'id',
          }),
          onValueChanged: (e)=> {
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendanceStatisticsListViewOpts'], 'selectedTeamIds', e.value);
            Attendees.attendanceStatistics.filtersForm.validate();
            const meets = $('div.selected-meets select').val();
            const categories = $('div.selected-categories select').val();
            if (meets && meets.length && categories && categories.length && Attendees.attendanceStatistics.attendancesDatagrid) {
              Attendees.attendanceStatistics.updateGatheringCountAndDatagrid();
            }
          },
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
          Attendees.attendanceStatistics.attendancesDatagrid = Attendees.attendanceStatistics.initFilteredAttendancesDatagrid(data, itemElement);
        },
      },
    ],
  },

  initFilteredAttendancesDatagrid: (data, itemElement) => {
    const $attendanceDatagrid = $("<div id='attendances-datagrid-container'>").dxDataGrid(Attendees.attendanceStatistics.attendanceDatagridConfig);
    itemElement.append($attendanceDatagrid);
    return $attendanceDatagrid.dxDataGrid('instance');
  },

  attendanceDatagridConfig: {
    dataSource: {
      store: new DevExpress.data.CustomStore({
        key: 'attending__attendee',
        load: (loadOptions) => {
          const meets = $('div.selected-meets select').val();
          const characters = $('div.selected-characters select').val();
          const categories = $('div.selected-categories select').val();
          const teams = $('div.selected-teams select').val();
          const deferred = $.Deferred();

          if (meets && meets.length && categories && categories.length) {
            const args = {
              "meets[]": meets,
              "categories[]": categories,
              take: 9999,
              start: $('div.filter-from input')[1].value ? new Date($('div.filter-from input')[1].value).toISOString() : null,
              finish: $('div.filter-till input')[1].value ? new Date($('div.filter-till input')[1].value).toISOString() : null,
            };

            if (characters && characters.length > 0) {
              args['characters[]'] = characters;
            }

            if (teams && teams.length > 0) {
              args['teams[]'] = teams;
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
              url: $('form.filters-dxform').data('attendance-stats-endpoint'),
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
                deferred.reject("Data Loading Error for attendance stats datagrid, probably time out?");
              },
              timeout: 60000,
            });
          } else {
            deferred.resolve([], {totalCount: 0, groupCount: 0});
          }
          return deferred.promise();
        },
      }),
    },
    export: {
      enabled: true,
      allowExportSelectedData: true,  // needs selection mode
    },
    selection: {
      mode: 'multiple',
      showCheckBoxesMode: 'onLongTap',
    },
    searchPanel: {
      visible: true,
      width: 150,
      placeholder: 'search name...',
    },
    allowColumnReordering: true,
    columnAutoWidth: true,
    allowColumnResizing: true,
    columnResizingMode: 'nextColumn',
    // cellHintEnabled: true,
    hoverStateEnabled: true,
    rowAlternationEnabled: true,
    remoteOperations: true,
    stateStoring: {
      enabled: true,
      type: 'sessionStorage',
      storageKey: Attendees.utilities.datagridStorageKeys['attendanceStatisticsListView'],
    },
    sorting: {
      mode: "multiple",
    },
    loadPanel: {
      message: 'Fetching...',
      enabled: true,
    },
    wordWrapEnabled: false,
    width: '100%',
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
              Attendees.attendanceStatistics.attendancesDatagrid.state(null);
              window.sessionStorage.removeItem('attendanceStatisticsListViewOpts');
              Attendees.utilities.selectAllGroupedTags(Attendees.attendanceStatistics.filtersForm.getEditor('characters'), []);
              Attendees.utilities.selectAllGroupedTags(Attendees.attendanceStatistics.filtersForm.getEditor('categories'), [9]);
              Attendees.utilities.selectAllGroupedTags(Attendees.attendanceStatistics.filtersForm.getEditor('teams'), []);
              Attendees.utilities.selectAllGroupedTags(Attendees.attendanceStatistics.filtersForm.getEditor('meets'), []);
              Attendees.attendanceStatistics.filtersForm.getEditor('filter-from').option('value', new Date(new Date().setHours(new Date().getHours() - 1)));
              Attendees.attendanceStatistics.filtersForm.getEditor('filter-till').option('value', new Date(new Date().setMonth(new Date().getMonth() + 1)));
            }
          },
        },
      });
    },
    onCellPrepared: e => e.rowType === "header" && e.column.dataHtmlTitle && e.cellElement.attr("title", e.column.dataHtmlTitle),
    columns: [
      {
        dataField: 'attendee',
        sortIndex: 1,
        sortOrder: 'asc',
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
        width: '30%',
        calculateDisplayValue: 'attending_name',  // can't use function when remoteOperations https://supportcenter.devexpress.com/ticket/details/t897726
        cellTemplate: (cellElement, cellInfo) => {
          let template = `<a title="Click to open a new page of the attendee info" target="_blank" href="/persons/attendee/${cellInfo.data.attending__attendee}">(Info)</a> <span>${cellInfo['displayValue']}</span>`;  // <span> required for filter highlight search text
          if (cellInfo.data.attending_name.includes(' by ')) {  // has registrant
            template += ` <a title="Click to open a new page of the registrant info" target="_blank" href="/persons/attendee/${cellInfo.data.attending__registration__registrant_id}">(Info)</a>`;
          }
          cellElement.append(template);
        },
        placeholder: "Select or search...",
        editorOptions: {
           noDataText: "Nothing! Ever enrolled?",
        },
        lookup: {},  // required for filter highlight search text
      },
      {
        dataField: 'count',
        sortIndex: 0,
        sortOrder: 'desc',
//        width: '10%',
        allowGrouping: false,
        caption: 'Attendance Count',
        dataType: 'number',
      },
      {
        dataField: 'characters',
//        width: '10%',
        allowGrouping: false,
        caption: 'Characters',
        dataType: 'string',
      },
      {
        dataField: 'teams',
//        width: '10%',
        allowGrouping: false,
        caption: 'Teams',
        dataType: 'string',
      },
    ],
  },
};

$(document).ready(() => {
  Attendees.attendanceStatistics.init();
});
