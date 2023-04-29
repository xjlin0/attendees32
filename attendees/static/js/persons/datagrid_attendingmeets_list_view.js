Attendees.attendingmeets = {
  filtersForm: null,
  meetScheduleRules: {},
  selectedMeetHasRule: false,
  allowEditingAttending: false,
  filterMeetCheckbox: null,
  attendingIds: null,
  gradeConverter: [],
  selectedMeetSlugs: [],
  meetData: null,
  init: () => {
    console.log('static/js/persons/datagrid_attendingmeets_list_view.js');
    Attendees.utilities.clearGridStatesInSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListView']); // remove saved search text without interfering column visibility
    Attendees.attendingmeets.initFilterMeetCheckbox();
    Attendees.attendingmeets.initEditingSwitch();
    Attendees.attendingmeets.initFiltersForm();
    Attendees.attendingmeets.gradeConverter = JSON.parse(document.querySelector('form.filters-dxform').dataset.gradeConverter);
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
          console.log("hi 32 initEditingSwitch onValueChanged here is e.value: ", e.value);
          Attendees.attendingmeets.toggleEditing(e.value);
        },
      })
    }
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

  setNewAttendeeLink: (selectedMeetSlugs) => {
    const addAttendeeLink = document.querySelector('a.add-attendee');

    if (addAttendeeLink) {
      const params = {familyName: 'without'};
      if (selectedMeetSlugs && selectedMeetSlugs.length === 1) {
        const meet = Attendees.attendingmeets.meetScheduleRules[selectedMeetSlugs[0]];
        params['joinMeetId'] = meet.id;
        params['joinMeetName'] = meet.name;
      }

      addAttendeeLink.classList.remove("btn-outline-secondary");
      addAttendeeLink.classList.add("btn-outline-success");
      addAttendeeLink.href = '/persons/attendee/new?' + new URLSearchParams(params).toString();
    }
  },

  toggleEditing: (enabled) => {
    if (Attendees.attendingmeets.attendingmeetsDatagrid) {
      Attendees.attendingmeets.attendingmeetsDatagrid.option('editing.allowUpdating', enabled);
      Attendees.attendingmeets.attendingmeetsDatagrid.option('editing.allowAdding', enabled);
      Attendees.attendingmeets.attendingmeetsDatagrid.option('editing.allowDeleting', enabled);
      Attendees.attendingmeets.attendingmeetsDatagrid.option('editing.popup.onContentReady', e => e.component.option('toolbarItems[0].visible', enabled));
    }
    console.log("hi 73 here is enabled: ", enabled);
    if (enabled) {
      Attendees.attendingmeets.setNewAttendeeLink(Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'selectedMeetSlugs'));
    } else {
      const addAttendeeLink = document.querySelector('a.add-attendee');
      if (addAttendeeLink) {
        addAttendeeLink.removeAttribute("href");
        addAttendeeLink.classList.add("btn-outline-secondary");
        addAttendeeLink.classList.remove("btn-outline-success");
      }
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
          type: 'datetime',
          value: new Date(
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterFromString') ?
              Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterFromString') :
              new Date().setHours(new Date().getHours() - 1)
          ),
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
          type: 'datetime',
          value: new Date(
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterTillString') ?
              Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'filterTillString') :
              new Date().setMonth(new Date().getMonth() + 1)
          ),
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
            if (Attendees.utilities.editingEnabled) { Attendees.attendingmeets.setNewAttendeeLink(e.value); }
            Attendees.attendingmeets.filtersForm.validate();
            const defaultHelpText = "Can't show schedules when multiple selected. Select single one to view its schedules";
            const $meetHelpText = Attendees.attendingmeets.filtersForm.getEditor('meets').element().parent().parent().find(".dx-field-item-help-text");
            Attendees.attendingmeets.selectedMeetHasRule = false;
            $meetHelpText.text(defaultHelpText);  // don't use itemOption!! https://supportcenter.devexpress.com/ticket/details/t531683
            if (e.value && e.value.length > 0) {
              const characters = $('div.selected-characters select').val();
              Attendees.attendingmeets.filtersForm.getEditor('characters').option('value', []);
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
                } else {
                  finalHelpText = noRuleText;
                }
                $meetHelpText.text(finalHelpText);  // https://supportcenter.devexpress.com/ticket/details/t531683
              }
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {grouping: 'assembly_name', model: 'attendingmeet'};  // for grouped: true,

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
                          Attendees.attendingmeets.meetScheduleRules[meet.slug] = {meetStart: meet.start, meetFinish: meet.finish, rules: meet.schedule_rules, character: meet.major_character, assembly: meet.assembly, id: meet.id, name: meet.display_name, defaultTillInWeeks: meet.infos['default_attendingmeet_in_weeks']};
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
                const params = {take: 9999, grouping: 'assembly_name'};  // for grouped: true,
                const meetSlugs = $('div.selected-meets select').val();
                const meets = meetSlugs && meetSlugs.length ? meetSlugs : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'selectedMeetSlugs');
                const assemblies = meets && meets.reduce((all, now) => {const meet = Attendees.attendingmeets.meetScheduleRules[now]; if(meet){all.add(meet.assembly)}; return all}, new Set());
                // const length = assemblies && assemblies.length
                if (assemblies && assemblies.size){
                  params['assemblies[]'] = Array.from(assemblies);
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

            if (Attendees.attendingmeets.attendingmeetsDatagrid) {
              args['take'] = Attendees.attendingmeets.attendingmeetsDatagrid.pageSize();
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
                  message: 'update attendingmeet success',
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
            url: $('form.filters-dxform').data('attendingmeets-endpoint'),
            method: 'POST',
            dataType: 'json',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(values),  // ...subject}),
            success: (result) => {
              DevExpress.ui.notify(
                {
                  message: 'Create attendingmeet success',
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
            url: $('form.filters-dxform').data('attendingmeets-endpoint') + key + '/' ,
            method: 'DELETE',
            success: (result) => {
              DevExpress.ui.notify(
                {
                  message: 'removed attendingmeet success',
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
      type: 'sessionStorage',
      storageKey: Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListView'],
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
       visible: true,
     },
    columnChooser: {
      enabled: true,
      mode: 'select',
    },
    sorting: {
      mode: "multiple",
    },
    onCellPrepared: e => e.rowType === "header" && e.column.dataHtmlTitle && e.cellElement.attr("title", e.column.dataHtmlTitle),

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
//        customizeItem: function(item) {
//          if (item.dataField === "attending") {
//            item.disabled = !Attendees.attendingmeets.allowEditingAttending;
//          }  // prevent users from changing attending to avoid data chaos
//        },
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
            editorType: 'dxTextArea',
            colSpan: 2,
            editorOptions: {
              autoResizeEnabled: true,
            },
          },
        ],
      },
    },
    onCellClick: (e) => {
        if (e.rowType === 'data' && e.column.dataField === 'attending' && e.event.target.nodeName === 'U') {
            e.component.editRow(e.row.rowIndex);
        }
    },
    onInitNewRow: (e) => {
      e.data.start = new Date();  //new Date().toLocaleDateString('sv');  // somehow new Date().toDateString() is UTC, Sweden locale "sv" uses the ISO 8601 format
      e.data.category = 1;  // scheduled
      Attendees.attendingmeets.attendingmeetsDatagrid.option('editing.popup.title', 'Adding AttendingMeet');
      const selectedMeetSlugs = Attendees.attendingmeets.filtersForm.getEditor('meets').option('value');
      if (selectedMeetSlugs && selectedMeetSlugs.length === 1) {
        const selectedMeet = Attendees.attendingmeets.meetScheduleRules[selectedMeetSlugs[0]];
        e.data.meet__assembly = selectedMeet.assembly;
        e.data.assembly = selectedMeet.assembly;
        e.data.meet = selectedMeet.id;
        if (selectedMeet['character']){
          e.data.character = selectedMeet['character'];
        }

        if (selectedMeet['defaultTillInWeeks']) {
          e.data.finish = new Date(new Date().setDate(new Date().getDate()*7 + selectedMeet['defaultTillInWeeks']));
        }
      }
//      Attendees.attendingmeets.allowEditingAttending = true;
    },
    onEditingStart: (e) => {
      const grid = e.component;
      grid.beginUpdate();
      if (e.data && typeof e.data === 'object') {
        const editingTitle = 'Editing enrollment: ' + e.data.attending__attendee || '';
        const readingTitle = 'Read only Info: ' + (e.data.attending__attendee || '') + ' (enable editing for modifications)';
        const title = Attendees.utilities.editingEnabled ? editingTitle : readingTitle;
        grid.option('editing.popup.title', title);
      }
//      Attendees.attendingmeets.allowEditingAttending = false;
      grid.option("columns").forEach(column => {
        grid.columnOption(column.dataField, "allowEditing", Attendees.utilities.editingEnabled);
      });
      grid.endUpdate();
    },
    columns: [
      {
        dataField: 'attending',
        sortOrder: 'asc',
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
        validationRules: [{type: 'required'}],
        calculateDisplayValue: 'attending__attendee',  // can't sort remotely for function https://supportcenter.devexpress.com/ticket/details/t897726
        cellTemplate: (cellElement, cellInfo) => {
          cellElement.append(`<a title="Click to open a new page of the attendee info" target="_blank" href="/persons/attendee/${cellInfo.data.attendee_id}">(Info)</a> <u title="click to see the enrollment details" role="button">${cellInfo['displayValue']}</u>`);
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
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
        validationRules: [{type: 'required'}],
        caption: 'Group (Assembly)',
        setCellValue: (newData, value, currentData) => {
          newData.assembly = value;
          newData.meet__assembly = value;
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
              load: (loadOptions) => {
                const deferred = $.Deferred();

                const args = Attendees.utilities.filterDevExtremeArgs(loadOptions, {
                                take: 9999,
                                searchOperation: loadOptions['searchOperation'],
                                searchValue: loadOptions['searchValue'],
                                searchExpr: loadOptions['searchExpr'],
                              });

                $.ajax({
                  url: $('form.filters-dxform').data('assemblies-endpoint'),
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
                    deferred.reject("Data Loading Error for assemblies lookup, probably time out?");
                  },
                  timeout: 5000,
                });

                return deferred.promise();
              },
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
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
        width: '10%',
        validationRules: [{type: 'required'}],
        setCellValue: (newData, value, currentData) => {
          newData.meet = value;
          newData.team = null;
          const [majorCharacter, tillInWeeks] = Attendees.attendingmeets.meetData[value];
          if (majorCharacter && !currentData.character) {newData.character = majorCharacter;}
          if (!currentData.finish) { newData.finish = new Date(new Date().setDate(new Date().getDate()*7 + (tillInWeeks || 99999))); }
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
                  searchOpts['model'] = 'attendingmeet';
                  if (options.data) {
                    searchOpts['assemblies[]'] = options.data.assembly;
                  }
                  $.getJSON($('form.filters-dxform').data('meets-endpoint-by-slug'), searchOpts)
                    .done((result) => {
                      if (result.data && Attendees.attendingmeets.meetData === null) {
                        Attendees.attendingmeets.meetData = result.data.reduce((all, now)=> {all[now.id] = [now.major_character, now.infos['default_attendingmeet_in_weeks']]; return all}, {});
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
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
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
                 if (options.data && options.data.meet__assembly) { // for popup editor dropdown limiting by chosen assembly
                   searchOpts['assemblies[]'] = options.data.meet__assembly;
                 } else {  // for datagrid column lookup limiting by assemblies
                   const meets = $('div.selected-meets select').val() || Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'selectedMeetSlugs');
                   const assemblies = meets && meets.reduce((all, now) => {const meet = Attendees.attendingmeets.meetScheduleRules[now]; if(meet){all.add(meet.assembly)}; return all}, new Set());
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
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
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
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
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
                  if (options.data && options.data.meet) {  // for popup editor drop down limiting by chosen meet
                    searchOpts['meets[]'] = options.data.meet;
                    delete searchOpts['filter'];
                  } else {  // for datagrid column lookup limiting by meet
                    const meetSlugs = $('div.selected-meets select').val();
                    const meets = meetSlugs.length ? meetSlugs : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['datagridAttendingmeetsListViewOpts'], 'selectedMeetSlugs');
                    if (meets && meets.length){
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
      {
        dataField: 'start',
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
        validationRules: [{type: 'required'}],
        dataType: 'datetime',
        format: 'MM/dd/yyyy',
        editorOptions: {
          type: 'datetime',
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        },
      },
      {
        dataField: 'attending__registration__registrant__infos__names__original',
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
        caption: 'Registrant',
        visible: false,
        allowEditing: false,
        cellTemplate: (cellElement, cellInfo) => {
          if (cellInfo && cellInfo['displayValue']) {
            cellElement.append(`<span>${cellInfo['displayValue']}</span> <a title="Click to open a new page of the registrant info" target="_blank" href="/persons/attendee/${cellInfo.data.registrant_attendee_id}">(Info)</a>`);
          }
        },
      },
      {
        dataField: 'attending__attendee__infos__fixed__grade',
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
        caption: 'Grade',
        visible: false,
        allowEditing: false,
        cellTemplate: (cellElement, cellInfo) => {
          if (cellInfo.displayValue) {
            cellElement.append ('<span>' + Attendees.attendingmeets.gradeConverter[parseInt(cellInfo.displayValue)] + '<span>');
          }
        }
      },
      {
        dataField: 'finish',
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
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
        allowGrouping: false,
        caption: 'Note',
        dataType: 'string',
      },
    ],
  },
};

$(document).ready(() => {
  Attendees.attendingmeets.init();
});
