Attendees.roster = {
  filtersForm: null,
  meetScheduleRules: {},
  buttonCategories: {},
  allCategories: {},
  selectedMeetHasRule: false,
  initialized: false,
  filterMeetCheckbox: null,
  loadOptions: null,
  selectedCharacterSlugs: [],
  selectedMeetSlugs: [],
  meetData: {},
  init: () => {
    console.log('static/js/occasions/roster_list_view.js');
    Attendees.roster.initFiltersForm();
  },

  updateAttendance: (event) => {
    const $radioInput = $(event.currentTarget);
    const rowIndex = $radioInput.prop('name');
    const categoryId = $radioInput.prop('value');
    Attendees.roster.attendancesDatagrid.cellValue(rowIndex, 'category', categoryId);
    Attendees.roster.attendancesDatagrid.saveEditData();
  },

  reloadRollCallerButtons: () => {
    $('div#attendances-datagrid-container').off('click', 'input.roll-call-button').on('click','input.roll-call-button', Attendees.roster.updateAttendance);
  },

  initFiltersForm: () => {
    $.ajaxSetup({
      headers: {
        'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
      }
    });
    Attendees.roster.filtersForm = $('form.filters-dxform').dxForm(Attendees.roster.filterFormConfigs).dxForm('instance');
    Attendees.roster.filtersForm.getEditor('meets').getDataSource().reload();
    Attendees.utilities.editingEnabled = true;
  },

  filterFormConfigs: {
    dataSource: null,
    colCount: 12,
    itemType: 'group',
    items: [
      {
        colSpan: 2,
        cssClass: 'filter-from',
        dataField: 'filter-from',
        helpText: `mm/dd/yyyy in ${Intl.DateTimeFormat().resolvedOptions().timeZone} timezone`,
        validationRules: [
          {
            type: 'required'
          },
          {
            reevaluate: true,
            type: 'custom',
            message: 'filter date "Till" is earlier than "From"',
            validationCallback: (e) => {
              const filterTill = $('div.filter-till input')[1].value;
              return e.value && filterTill ? new Date(filterTill) > e.value : true;
            },
          }
        ],
        label: {
          location: 'top',
          text: 'From (mm/dd/yyyy)',
        },
        editorType: 'dxDateBox',
        editorOptions: {
          value: new Date(new Date().setDate(new Date().getDate() - 1)),
          type: 'datetime',
          onValueChanged: (e) => {
            Attendees.roster.filtersForm.getEditor('gatherings').option('value', null);
            Attendees.roster.filtersForm.getEditor('gatherings').getDataSource().reload();
          },
        },
      },
      {
        colSpan: 2,
        cssClass: 'filter-till',
        dataField: 'filter-till',
        helpText: `mm/dd/yyyy in ${Intl.DateTimeFormat().resolvedOptions().timeZone} timezone`,
        validationRules: [
          {
            type: 'required'
          },
          {
            reevaluate: true,
            type: 'custom',
            message: 'filter date "Till" is earlier than "From"',
            validationCallback: (e) => {
              const filterFrom = $('div.filter-from input')[1].value;
              return e.value && filterFrom ? new Date(filterFrom) < e.value : true;
          },
        }],
        label: {
          location: 'top',
          text: 'Till(exclude)',
        },
        editorType: 'dxDateBox',
        editorOptions: {
          value: new Date(new Date().setDate(new Date().getDate() + 6)),
          type: 'datetime',
          onValueChanged: (e) => {
            Attendees.roster.filtersForm.getEditor('gatherings').option('value', null);
            Attendees.roster.filtersForm.getEditor('gatherings').getDataSource().reload();
          },
        },
      },
      {
        dataField: 'meets',
        colSpan: 3,
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
            Attendees.roster.filtersForm.getEditor('gatherings').option('value', null);
            Attendees.roster.filtersForm.validate();
            const defaultHelpText = "Can't show schedules when multiple selected. Select single one to view its schedules.";
            const $meetHelpText = Attendees.roster.filtersForm.getEditor('meets').element().parent().parent().find(".dx-field-item-help-text");
            Attendees.roster.selectedMeetHasRule = false;
            $meetHelpText.text(defaultHelpText);  // https://supportcenter.devexpress.com/ticket/details/t531683

            if (e.value && Object.keys(Attendees.roster.meetScheduleRules).length > 0) {
              Attendees.roster.filtersForm.getEditor('gatherings').getDataSource().reload();
              Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['rollCallListViewOpts'], 'selectedMeetSlugs', e.value);
              Attendees.roster.attendancesDatagrid.refresh();
              const newHelpTexts = [];
              let finalHelpText = '';
              let lastDuration = 0;
              const noRuleText = 'This meet does not have schedules in EventRelation';
              const ruleData = Attendees.roster.meetScheduleRules[ e.value ];
              const timeRules = ruleData.rules;
              const meetStart = new Date(ruleData.meetStart).toDateString();
              const meetFinish = new Date(ruleData.meetFinish).toDateString();
              if (timeRules && timeRules.length > 0) {
                timeRules.forEach(timeRule => {
                  if (timeRule.rule) {
                    Attendees.roster.selectedMeetHasRule = true;
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
                const filterFrom = $('div.filter-from input')[1].value;
                const filterTill = $('div.filter-till input')[1].value;
                const d = new $.Deferred();
                const params = {
                  start: new Date(filterFrom).toISOString(),
                  finish: new Date(filterTill).toISOString(),
                  grouping: 'assembly_name',  // for grouped: true
                  model: 'attendance',  // for suppressing no-attendance meets such as believe
                };

                $.get($('form.filters-dxform').data('meets-endpoint-by-slug'), params)
                  .done((result) => {
                    d.resolve(result.data);
                    if (Object.keys(Attendees.roster.meetScheduleRules).length < 1 && result.data && result.data[0]) {
                      result.data.forEach( assembly => {
                        assembly.items.forEach( meet => {
                          Attendees.roster.meetScheduleRules[meet.slug] = {meetStart: meet.start, meetFinish: meet.finish, rules: meet.schedule_rules, assembly: meet.assembly};
                          Attendees.roster.meetData[meet.id] = [meet.finish, meet.major_character];  // cache the every meet's major characters for later use
                        })
                      });
                    }
                    const selectedMeetSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['rollCallListViewOpts'], 'selectedMeetSlugs');
                    if (selectedMeetSlugs) {
                      Attendees.roster.filtersForm.getEditor('meets').option('value', selectedMeetSlugs);
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
        dataField: 'gatherings',
        colSpan: 5,
        helpText: 'Select one to filter results',
        cssClass: 'selected-gatherings',
        validationRules: [{type: 'required'}],
        label: {
          location: 'top',
          text: 'Select a gathering',
        },
        editorType: 'dxSelectBox',
        editorOptions: {
          valueExpr: 'id',
          displayExpr: 'display_name',  // gathering service only support search in display_name, not gathering_name
          searchEnabled: true,
          onValueChanged: (e)=> {
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['rollCallListViewOpts'], 'selectedGatheringId', e.value);
            Attendees.roster.filtersForm.validate();
            const meet = Attendees.roster.filtersForm.getEditor('meets').option('value');
            if (e.value && meet && Attendees.roster.attendancesDatagrid) {
              Attendees.roster.attendancesDatagrid.refresh();
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: (searchOpts) => {
                const filterFrom = $('div.filter-from input')[1].value;
                const filterTill = $('div.filter-till input')[1].value;
                const d = new $.Deferred();
                const meet = Attendees.roster.filtersForm.getEditor('meets').option('value');
                if (meet) {
                  const params = {
                    take: 9999,
                    meets: [meet],
                    start: new Date(filterFrom).toISOString(),
                    finish: new Date(filterTill).toISOString(),
                  };

                  if (searchOpts['searchValue']) {
                    params['searchValue'] = searchOpts['searchValue'];
                    params['searchOperation'] = searchOpts['searchOperation'];
                    params['searchExpr'] = searchOpts['searchExpr'];
                  }

                  $.get($('form.filters-dxform').data('gatherings-endpoint'), params)
                    .done((result) => {
                      d.resolve(result.data);
                      // const selectedGatheringId = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['rollCallListViewOpts'], 'selectedGatheringId');
                      // if (selectedGatheringId) {
                      //   Attendees.roster.filtersForm.getEditor('gatherings').option('value', selectedMeetSlugs[0]);
                      // }
                    });
                } else {
                  d.resolve([], {totalCount: 0, groupCount: 0});
                }
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
          Attendees.roster.attendancesDatagrid = Attendees.roster.initFilteredattendancesDatagrid(data, itemElement);
        },
      },
    ],
  },

  initFilteredattendancesDatagrid: (data, itemElement) => {
    const $attendanceDatagrid = $("<div id='attendances-datagrid-container'>").dxDataGrid(Attendees.roster.attendanceDatagridConfig);
    itemElement.append($attendanceDatagrid);
    return $attendanceDatagrid.dxDataGrid('instance');
  },

  attendanceDatagridConfig: {
    dataSource: {
      store: new DevExpress.data.CustomStore({
        key: 'id',
        load: (loadOptions) => {
          Attendees.roster.loadOptions = loadOptions;
          const deferred = $.Deferred();
          const filterFrom = $('div.filter-from input')[1].value;
          const filterTill = $('div.filter-till input')[1].value;
          const meet = Attendees.roster.filtersForm.getEditor('meets').option('value');
          const gathering = Attendees.roster.filtersForm.getEditor('gatherings').option('value');

          if (meet && gathering && filterFrom && filterTill) {
            const args = {
              start: new Date(filterFrom).toISOString(),
              finish: new Date(filterTill).toISOString(),
              meets: [meet],
              gatherings: [gathering],
              photoInsteadOfGatheringAssembly: true,
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
                if (result.totalCount > 0) {
                  Attendees.roster.reloadRollCallerButtons();
                }
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
      placeholder: 'search name or notes ...',
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
    wordWrapEnabled: true,
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
    onOptionChanged: (e) => {  // https://supportcenter.devexpress.com/ticket/details/t710995
      if(['paging.pageSize', 'paging.pageIndex'].includes(e.fullName)) {
        Attendees.roster.reloadRollCallerButtons();
      }
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
              Attendees.roster.attendancesDatagrid.state(null);
              window.sessionStorage.removeItem(Attendees.utilities.datagridStorageKeys['rollCallListViewOpts']);
              Attendees.roster.filtersForm.getEditor('meets').option('value', null);
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
        // onContentReady: e => e.component.option('toolbarItems[0].visible', false),  // assembly
      },
      form: {
        colCount: 2,
        items: [
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
           dataField: 'infos.note',
           helpText: 'special memo',
           editorOptions: {
             autoResizeEnabled: true,
           },
         },
//          {
//            dataField: 'start',
//            helpText: 'participation start time in browser timezone',
//          },
//          {
//            dataField: 'finish',
//            helpText: 'participation end time in browser timezone',
//          },
        ],
      },
    },
    onCellClick: (e) => {
      if (e.rowType === 'data' && e.column.dataField === 'photo') {
        e.component.editRow(e.row.rowIndex);
      }
    },
    onInitNewRow: (e) => {
      e.data.start = new Date();
      Attendees.roster.attendancesDatagrid.option('editing.popup.title', 'Adding Attendance');
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
        dataField: 'photo',
        width: 100,
        allowFiltering: false,
        allowSorting: false,
        allowGrouping: false,
        cellTemplate: (container, options) => {
          $('<div>')
            .append($('<img>', { class: 'attendee-photo-img', src: options.value }))
            .appendTo(container);
        },
      },
      {
        dataField: 'attending',
        width: 200,
        validationRules: [{type: 'required'}],
        calculateDisplayValue: 'attending_name',  // can't use function when remoteOperations https://supportcenter.devexpress.com/ticket/details/t897726
        cellTemplate: (cellElement, cellInfo) => {  // squeeze to name column for better mobile experience.
          cellElement.append ('<strong>' + cellInfo.displayValue + '</strong><br>');
          const buttonCategoryKeys = Object.keys(Attendees.roster.buttonCategories);
          if (cellInfo && cellInfo.data && buttonCategoryKeys.length > 0) {
            let html = `<div class="btn-group-vertical btn-group-sm roll-call-button-group"
                             role="group">`;
            buttonCategoryKeys.forEach((categoryId, index) => {
              const buttonCategory = Attendees.roster.buttonCategories[categoryId];
              const buttonId = `btn-${cellInfo.data.id}-${categoryId}`;
              html += `<input type="radio"
                              class="btn-check roll-call-button"
                              name="${cellInfo.rowIndex}"
                              id="${buttonId}"
                              value="${categoryId}"
                              autocomplete="off"
                              ${cellInfo.data.category && cellInfo.data.category.toString() === categoryId ? 'checked' : ''}>
                       <label class="roll-call btn ${buttonCategory.class}"
                              for="${buttonId}">
                         ${buttonCategory.label}
                       </label>`
            });
            html += '</div>';
            if (cellInfo.data.category !== 1 && !(cellInfo.data.category in Attendees.roster.buttonCategories)) {  // 1 is scheduled
              html += `<button disabled
                               type="button"
                               class="btn btn-sm btn-secondary"
                               value="Other">
                         ${Attendees.roster.allCategories[cellInfo.data.category]}
                       </button>`
            }
            cellElement.append(html)
          }
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'attending_label',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: (loadOptions) => {
                const deferred = $.Deferred();
                const filterFrom = $('div.filter-from input')[1].value;
                const filterTill = $('div.filter-till input')[1].value;
                const meet = Attendees.roster.filtersForm.getEditor('meets').option('value');
                const gathering = Attendees.roster.filtersForm.getEditor('gatherings').option('value');
                loadOptions['sort'] = Attendees.roster.attendancesDatagrid && Attendees.roster.attendancesDatagrid.getDataSource().loadOptions().group;
                const args = {
                  searchOperation: loadOptions['searchOperation'],
                  searchValue: loadOptions['searchValue'],
                  searchExpr: loadOptions['searchExpr'],
                  start: new Date(filterFrom).toISOString(),
                  finish: new Date(filterTill).toISOString(),
                };

                if (meet) {
                  args['meets'] = [meet];
                }

                if (gathering) {
                  args['gatherings'] = [gathering];
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
      {
        dataField: 'character',
        groupIndex: 0,
        validationRules: [{type: 'required'}],
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
                 const meets = [ Attendees.roster.filtersForm.getEditor('meets').option('value') || Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['rollCallListViewOpts'], 'selectedMeetSlugs') ];
                 const assemblies = meets && meets.reduce((all, now) => {const meet = Attendees.roster.meetScheduleRules[now]; if(meet){all.add(meet.assembly)}; return all}, new Set());
                 if (assemblies && assemblies.size){
                   searchOpts['assemblies[]'] = Array.from(assemblies);
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
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: (options) => {
            return {
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  const d = new $.Deferred();
                  searchOpts['type'] = 'attendance';
                  searchOpts['take'] = 9999;
                  $.get($('form.filters-dxform').data('categories-endpoint'), searchOpts)
                    .done((result) => {
                      d.resolve(result.data);
                      if (Object.keys(Attendees.roster.buttonCategories).length < 1 && result.data && result.data[0]) {
                        result.data.forEach( category => {
                          if (category && category.infos && category.infos.ROSTER_DATA_DO_NOT_CHANGE) {
                            Attendees.roster.buttonCategories[category.id] = category.infos.ROSTER_DATA_DO_NOT_CHANGE
                          }
                          Attendees.roster.allCategories[category.id] = category.display_name;
                        });
                      }
                    });
                return d.promise();
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
                    const meet = Attendees.roster.filtersForm.getEditor('meets').option('value');
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
     {
       dataField: 'infos.note',
       caption: 'Note',
       dataType: 'string',
     },
    ],
  },
};

$(document).ready(() => {
  Attendees.roster.init();
});
