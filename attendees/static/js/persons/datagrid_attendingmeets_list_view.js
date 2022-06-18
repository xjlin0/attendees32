Attendees.attendingmeets = {
  filtersForm: null,
  meetScheduleRules: {},
  selectedMeetHasRule: false,
  initialized: false,
  filterMeetCheckbox: null,
  attendingIds: null,
  selectedCharacterSlugs: [],
  selectedMeetSlugs: [],
  meetData: null,
  init: () => {
    console.log('static/js/persons/datagrid_attendingmeets_list_view.js');
    Attendees.attendingmeets.initFilterMeetCheckbox();
    Attendees.attendingmeets.initEditingSwitch();
    Attendees.attendingmeets.initFiltersForm();
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

  toggleEditing: (enabled) => {
    if (Attendees.attendingmeets.attendingmeetsDatagrid) {
      Attendees.attendingmeets.attendingmeetsDatagrid.option('editing.allowUpdating', enabled);
      Attendees.attendingmeets.attendingmeetsDatagrid.option('editing.allowAdding', enabled);
      Attendees.attendingmeets.attendingmeetsDatagrid.option('editing.allowDeleting', enabled);
      Attendees.attendingmeets.attendingmeetsDatagrid.option('editing.popup.onContentReady', e => e.component.option('toolbarItems[0].visible', enabled));
    }
    const addAttendeeLink = document.querySelector('a.add-attendee');
    if (enabled) {
      addAttendeeLink.classList.remove("btn-outline-secondary");
      addAttendeeLink.classList.add("btn-outline-success");
      addAttendeeLink.href = '/persons/attendee/new?familyName=without';
    } else {
      addAttendeeLink.removeAttribute("href");
      addAttendeeLink.classList.add("btn-outline-secondary");
      addAttendeeLink.classList.remove("btn-outline-success");

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
        helpText: `mm/dd/yyyy in ${Intl.DateTimeFormat().resolvedOptions().timeZone} timezone`,
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
          value: Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterFromString') === undefined ? new Date(new Date().setHours(new Date().getHours() - 1)) : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterFromString') ? Date.parse(Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterFromString')) : null,
          type: 'datetime',
          onValueChanged: (e) => {
            const filterFromString = e.value ? e.value.toJSON() : null;  // it can be null to get all rows
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterFromString', filterFromString);
            // Attendees.attendingmeets.generateGatheringsButton.option('disabled', !Attendees.attendingmeets.readyToGenerate());
            if (Attendees.attendingmeets.filterMeetCheckbox.option('value')) {
              Attendees.attendingmeets.filtersForm.getEditor('meets').getDataSource().reload();
            }
            const meets = $('div.selected-meets select').val();
            const characters = $('div.selected-characters select').val();
            if (meets.length && characters.length) {
              Attendees.attendingmeets.attendingmeetsDatagrid.refresh();
            }
          },
        },
      },
      {
        colSpan: 3,
        cssClass: 'filter-till',
        dataField: 'filter-till',
        helpText: `mm/dd/yyyy in ${Intl.DateTimeFormat().resolvedOptions().timeZone} timezone`,
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
          value: Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterTillString') === undefined ? new Date(new Date().setMonth(new Date().getMonth() + 1)) : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterTillString') ? Date.parse(Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterTillString')) : null,
          type: 'datetime',
          onValueChanged: (e) => {
            // Attendees.attendingmeets.generateGatheringsButton.option('disabled', !Attendees.gatherings.readyToGenerate());
            const filterTillString = e.value ? e.value.toJSON() : null;  // it can be null to get all rows
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterTillString', filterTillString);
            if (Attendees.attendingmeets.filterMeetCheckbox.option('value')) {
              Attendees.attendingmeets.filtersForm.getEditor('meets').getDataSource().reload();
            }  // allow users to screen only active meets by meet's start&finish
            const meets = $('div.selected-meets select').val();
            const characters = $('div.selected-characters select').val();
            if (meets.length && characters.length) {
              Attendees.attendingmeets.attendingmeetsDatagrid.refresh();
            }
          },
        },
      },
      {
        dataField: 'meets',
        colSpan: 6,
        helpText: "Can't show schedules when multiple selected. Select single one to view its schedules",
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
                  Attendees.utilities.selectAllGroupedTags(Attendees.attendingmeets.filtersForm.getEditor('meets'));
                },
              },
            }
          ],
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
          onValueChanged: (e)=> {
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'selectedMeetSlugs', e.value);
            Attendees.attendingmeets.filtersForm.validate();
            const defaultHelpText = "Can't show schedules when multiple selected. Select single one to view its schedules";
            const $meetHelpText = Attendees.attendingmeets.filtersForm.getEditor('meets').element().parent().parent().find(".dx-field-item-help-text");
            Attendees.attendingmeets.selectedMeetHasRule = false;
            // Attendees.attendingmeets.generateGatheringsButton.option('disabled', true);
            $meetHelpText.text(defaultHelpText);  // https://supportcenter.devexpress.com/ticket/details/t531683
            if (e.value && e.value.length > 0) {
              const characters = $('div.selected-characters select').val();
              Attendees.attendingmeets.filtersForm.getEditor('characters').getDataSource().reload();
              if (characters.length) {
                Attendees.attendingmeets.attendingmeetsDatagrid.refresh();
              }
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
                  // if (Attendees.attendingmeets.selectedMeetHasRule && $('div#custom-control-edit-switch').dxSwitch('instance').option('value') && lastDuration > 0) {
                  //   Attendees.attendingmeets.generateGatheringsButton.option('disabled', false);
                  // }
                } else {
                  finalHelpText = noRuleText;
                }
                $meetHelpText.text(finalHelpText);  // https://supportcenter.devexpress.com/ticket/details/t531683
                // Attendees.attendingmeets.filtersForm.itemOption('duration', {editorOptions: {value: lastDuration}});
              }
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {grouping: 'assembly_name'};  // for grouped: true,

                if (Attendees.attendingmeets.filterMeetCheckbox.option('value')) {
                  const filterFrom = $('div.filter-from input')[1].value;
                  const filterTill = $('div.filter-till input')[1].value;
                  params['start'] = filterFrom ? new Date(filterFrom).toISOString() : null;
                  params['finish'] = filterTill ? new Date(filterTill).toISOString() : null;
                  // params['grouping'] = 'assembly_name';  // for grouped: true,
                }
                $.get($('form.filters-dxform').data('meets-endpoint-by-slug'), params)
                  .done((result) => {
                    d.resolve(result.data);
                    if (Object.keys(Attendees.attendingmeets.meetScheduleRules).length < 1 && result.data && result.data[0]) {
                      result.data.forEach( assembly => {
                        assembly.items.forEach( meet => {
                          Attendees.attendingmeets.meetScheduleRules[meet.slug] = {meetStart: meet.start, meetFinish: meet.finish, rules: meet.schedule_rules, assembly: meet.assembly};
                        })
                      }); // schedule rules needed for attendingmeets generation
                    }
                    const selectedMeetSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'selectedMeetSlugs') || [];
                    Attendees.utilities.selectAllGroupedTags(Attendees.attendingmeets.filtersForm.getEditor('meets'), selectedMeetSlugs);
                    Attendees.attendingmeets.filtersForm.getEditor('characters').getDataSource().reload();
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
                  Attendees.utilities.selectAllGroupedTags(Attendees.attendingmeets.filtersForm.getEditor('characters'));
                },
              },
            }
          ],
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
          onValueChanged: (e)=> {
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'selectedCharacterSlugs', e.value);
            Attendees.attendingmeets.filtersForm.validate();
            const meets = $('div.selected-meets select').val();
            if (meets.length && e.value && e.value.length > 0 && Attendees.attendingmeets.attendingmeetsDatagrid) {
              Attendees.attendingmeets.attendingmeetsDatagrid.refresh();
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {take: 9999};
                const meetSlugs = $('div.selected-meets select').val();
                const meets = meetSlugs && meetSlugs.length ? meetSlugs : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'selectedMeetSlugs');
                const assemblies = meets && meets.reduce((all, now) => {const meet = Attendees.attendingmeets.meetScheduleRules[now]; if(meet){all.add(meet.assembly)}; return all}, new Set());
                // const length = assemblies && assemblies.length
                if (assemblies && assemblies.size){
                  params['assemblies[]'] = Array.from(assemblies);
                }
                if (Attendees.attendingmeets.filterMeetCheckbox.option('value')) {
                  params['grouping'] = 'assembly_name';  // for grouped: true,
                }
                $.get($('form.filters-dxform').data('characters-endpoint'), params)
                  .done((result) => {
                    d.resolve(result.data);
                    const selectedCharacterSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'selectedCharacterSlugs') || [];
                    Attendees.utilities.selectAllGroupedTags(Attendees.attendingmeets.filtersForm.getEditor('characters'), selectedCharacterSlugs);
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
        dataField: "filtered_attendingmeet_set",
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

  initFilteredAttendingmeetsDatagrid: (data, itemElement) => {
    const $attendingmeetDatagrid = $("<div id='attendingmeets-datagrid-container'>").dxDataGrid(Attendees.attendingmeets.attendingmeetDatagridConfig);
    itemElement.append($attendingmeetDatagrid);
    return $attendingmeetDatagrid.dxDataGrid('instance');
  },

  attendingmeetDatagridConfig: {
    dataSource: {
      store: new DevExpress.data.CustomStore({
        key: 'id',
        load: (loadOptions) => {
          const meets = $('div.selected-meets select').val();
          const characters = $('div.selected-characters select').val();
          const deferred = $.Deferred();

          if (meets && meets.length > 0) {
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
              url: $('form.filters-dxform').data('attendingmeets-endpoint'),
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
                deferred.reject("Data Loading Error for attendingmeet datagrid, probably time out?");
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
    searchPanel: {
      visible: true,
      width: 300,
      placeholder: 'search attending or team/category ...',
    },
    allowColumnReordering: true,
    columnAutoWidth: true,
    allowColumnResizing: true,
    columnResizingMode: 'nextColumn',
    // cellHintEnabled: true,
    hoverStateEnabled: true,
    rowAlternationEnabled: true,
    remoteOperations: { groupPaging: true },
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
      type: 'custom',
      storageKey: Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListView'],
      customSave: (state) => {
        for (item in state) {
          if (['searchText'].includes(item)) delete state[item];
        }
        window.sessionStorage.setItem(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListView'], JSON.stringify(state));
      },
      customLoad: () => {
        return window.sessionStorage.getItem(this.storageKey);
      },
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
          icon: 'pulldown',
          onClick() {
            if(confirm('Are you sure to reset all settings (Sort/Group/Columns/Meets/Character/Time) in this page?')) {
              Attendees.attendingmeets.attendingmeetsDatagrid.state(null);
              window.sessionStorage.removeItem(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts']);
              Attendees.utilities.selectAllGroupedTags(Attendees.attendingmeets.filtersForm.getEditor('characters'), []);
              Attendees.utilities.selectAllGroupedTags(Attendees.attendingmeets.filtersForm.getEditor('meets'), []);
              Attendees.attendingmeets.filtersForm.getEditor('filter-from').option('value', new Date(new Date().setHours(new Date().getHours() - 1)));
              Attendees.attendingmeets.filtersForm.getEditor('filter-till').option('value', new Date(new Date().setMonth(new Date().getMonth() + 1)));
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
        title: 'attendingmeetEditingArgs',
        onContentReady: e => e.component.option('toolbarItems[0].visible', false),
      },
      form: {
        colCount: 2,
        items: [
          {
            dataField: 'meet__assembly',
            helpText: "Select to filter meet and character",
          },
          {
            dataField: 'meet',
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
            helpText: 'participation start time in browser timezone',
          },
          {
            dataField: 'finish',
            helpText: 'participation end time in browser timezone',
          },
          {
            dataField: 'infos.note',
            helpText: 'special memo',
            editorOptions: {
              autoResizeEnabled: true,
            },
          },
          {
            dataField: 'create_attendances_till',
            disabled: true,
            helpText: 'Auto create future attendances (not supported yet)',
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
      e.data.start = new Date();
      Attendees.attendingmeets.attendingmeetsDatagrid.option('editing.popup.title', 'Adding AttendingMeet');
    },
    onEditingStart: (e) => {
      const grid = e.component;
      grid.beginUpdate();

      if (e.data && typeof e.data === 'object') {
        const title = Attendees.utilities.editingEnabled ? 'Editing Attending meet' : 'Read only Info, please enable editing for modifications';
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
        calculateDisplayValue: (rowData) => rowData.attending__registration__attendee ? `(${rowData.attending__registration__attendee}) ${rowData.attending__attendee}` : rowData.attending__attendee,
        cellTemplate: (cellElement, cellInfo) => {
          cellElement.append ('<u role="button"><strong>' + cellInfo.displayValue + '</strong></u>');
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'attending_label',
          dataSource: (options) => {
            return {
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (loadOptions) => {
                  const meets = $('div.selected-meets select').val();
                  const characters = $('div.selected-characters select').val();
                  const deferred = $.Deferred();

                  if (meets && meets.length > 0) {
                    loadOptions['group'] = Attendees.attendingmeets.attendingmeetsDatagrid && Attendees.attendingmeets.attendingmeetsDatagrid.getDataSource().loadOptions().group;
                    loadOptions['take'] = Attendees.attendingmeets.attendingmeetsDatagrid && Attendees.attendingmeets.attendingmeetsDatagrid.pageSize();
                    loadOptions['skip'] = Attendees.attendingmeets.attendingmeetsDatagrid && (Attendees.attendingmeets.attendingmeetsDatagrid.pageIndex()*loadOptions['take']);
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
                      'group',
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
                          summary: result.summary,
                          groupCount: result.groupCount,
                        });
                      },
                      error: () => {
                        deferred.reject("Data Loading Error for attending lookup, probably time out?");
                      },
                      timeout: 10000,
                    });
                  } else {
                    deferred.resolve([], {totalCount: 0, groupCount: 0});
                  }
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
            }
          }
        },
      },
      {
        dataField: 'meet__assembly',
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
        dataField: 'meet',
        width: '10%',
        validationRules: [{type: 'required'}],
        setCellValue: (newData, value, currentData) => {
          newData.meet = value;
          newData.team = null;
          const [finish, majorCharacter] = Attendees.attendingmeets.meetData[value];
          if (majorCharacter && !currentData.character) {newData.character = majorCharacter;}
          if (!currentData.finish) { newData.finish = new Date(finish); }
        },
        editorOptions: {
          placeholder: 'Example: "The Rock"',
        },
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: (options) => {
            return {
              // filter: options.data ? {'assemblies[]': options.data.assembly} : null,
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  const d = new $.Deferred();
                  $.getJSON($('form.filters-dxform').data('meets-endpoint-by-slug'), searchOpts)
                    .done((result) => {
                      if (result.data && Attendees.attendingmeets.meetData === null) {
                        Attendees.attendingmeets.meetData = result.data.reduce((all, now)=> {all[now.id] = [now.finish, now.major_character]; return all}, {});
                      }  // cache the every meet's major characters for later use
                      d.resolve(result.data);
                    });
                  return d.promise();
                },
                byKey: (key) => {
                  return $.getJSON($('form.filters-dxform').data('meets-endpoint-by-slug') + key + '/');
                },
              }),
            };
          },
        },
      },
      {
        dataField: 'character',
        validationRules: [{type: 'required'}],
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: (options) => {
            return {
              // filter: options.data ? {'assemblies[]': options.data.assembly} : null,
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  searchOpts['take'] = 9999;
                  const meets = $('div.selected-meets select').val() || Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'selectedMeetSlugs');
                  const assemblies = meets && meets.reduce((all, now) => {const meet = Attendees.attendingmeets.meetScheduleRules[now]; if(meet){all.add(meet.assembly)}; return all}, new Set());
                  if (assemblies && assemblies.size){
                    searchOpts['assemblies[]'] = Array.from(assemblies);
                  }
//                  if (options.data && options.data.assembly) {searchOpts['assemblies[]'] = options.data.assembly; }
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
              // filter: options.data ? {'meets[]': [options.data.meet]} : null,
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  searchOpts['take'] = 9999;
                  const meetSlugs = $('div.selected-meets select').val();
                  const meets = meetSlugs.length ? meetSlugs : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'selectedMeetSlugs');
                  if (meets && meets.length){
                    searchOpts['assemblies[]'] = meets;
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
      {
        dataField: 'create_attendances_till',
        visible: false,
        dataType: 'datetime',
        label: {
          text: 'Reserve attendances to',
        },
        editorOptions: {
          type: 'datetime',
          showClearButton: true,
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        }
      },
      {
        dataField: 'start',
        validationRules: [{type: 'required'}],
        dataType: 'datetime',
        format: 'MM/dd/yyyy',
        editorOptions: {
          type: 'datetime',
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        },
      },
      {
        dataField: 'finish',
        validationRules: [{type: 'required'}],
        dataType: 'datetime',
        format: 'MM/dd/yyyy',
        editorOptions: {
          type: 'datetime',
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        },
      },
      {
        dataField: 'infos.note',
        visible: false,
        caption: 'Note',
        dataType: 'string',
      },
    ],
  },
};

$(document).ready(() => {
  Attendees.attendingmeets.init();
});
