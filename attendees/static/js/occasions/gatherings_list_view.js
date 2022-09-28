Attendees.gatherings = {
  filtersForm: null,
  meetScheduleRules: {},
  meetData: {},
  selectedMeetHasRule: false,
  generateGatheringsButton: null,
  filterMeetCheckbox: null,
  contentTypeEndpoint: '',
  contentTypeEndpoints: {},
  init: () => {
    console.log('static/js/occasions/gatherings_list_view.js');
    Attendees.utilities.clearGridStatesInSessionStorage(Attendees.utilities.datagridStorageKeys['gatheringsListView']); // remove saved search text without interfering column visibility
    Attendees.gatherings.initFilterMeetCheckbox();
    Attendees.gatherings.initEditingSwitch();
    Attendees.gatherings.initFiltersForm();
    Attendees.gatherings.initGenerateButton();
    Attendees.gatherings.filtersForm.validate();
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
          Attendees.gatherings.toggleEditing(e.value);
        },
      })
    }
  },

  initFilterMeetCheckbox: () => {
    Attendees.gatherings.filterMeetCheckbox = $('div#custom-control-filter-meets-checkbox').dxCheckBox({
      value: true,
      hint: 'When checked, the dropdown list of Meets will be filtered based on the From/Till date&time',
      text: 'Filter meets by date/time',
      onValueChanged: (e) => {
        Attendees.gatherings.filtersForm.getEditor('meets').getDataSource().reload();
      }
    }).dxCheckBox('instance');
  },

  initGenerateButton: () => {
    const generateGatheringsButtonDiv = document.querySelector('div#generate-gatherings');
    if (generateGatheringsButtonDiv) {
      Attendees.gatherings.generateGatheringsButton = $('div#generate-gatherings').dxButton({
        disabled: true,
        text: 'Generate Gatherings',
        height: '1.5rem',
        hint: 'Disabled when multiple meets selected or no duration filled',
        onClick: () => {
          if (Attendees.gatherings.filtersForm.validate().isValid && confirm('Are you sure to auto generate all gatherings of the chosen meet between the filtered date?')) {
            const params = {};
            const filterFrom = $('div.filter-from input')[1].value;
            const filterTill = $('div.filter-till input')[1].value;
            params['begin'] = filterFrom ? new Date(filterFrom).toISOString() : null;
            params['end'] = filterTill ? new Date(filterTill).toISOString() : null;
            if (Attendees.gatherings.selectedMeetHasRule && Attendees.gatherings.selectedMeetHasRule < 2) {
              params['duration'] = Attendees.gatherings.filtersForm.getEditor('duration').option('value');
            }
            const meetSlugs = $('div.selected-meets select').val();
            if (params['begin'] && params['end'] && Attendees.gatherings.filtersForm.validate().isValid && meetSlugs.length && meetSlugs.length === 1) {
              params['meet_slug'] = meetSlugs[0];
              return $.ajax({
                url: $('form.filters-dxform').data('series-gatherings-endpoint'),
                method: 'POST',
                dataType: 'json',
                contentType: 'application/json; charset=utf-8',
                data: JSON.stringify(params),
                success: (result) => {
                  DevExpress.ui.notify(
                    {
                      message: 'Batch processed, ' + result.number_created + ' successfully created between ' + new Date(result.begin).toLocaleString() + ' & ' + new Date(result.end).toLocaleString(),
                      position: {
                        my: 'center',
                        at: 'center',
                        of: window,
                      },
                    }, 'success', 3000);
                },
                error: (result) => {
                  console.log("hi gatherings_list_view.js 86 here is error result: ", result);
                  DevExpress.ui.notify(
                    {
                      message: 'Batch processing error. ' + result && result.responseText,
                      position: {
                        my: 'center',
                        at: 'center',
                        of: window,
                      },
                    }, 'error', 5000);
                },
                complete: () => {
                  Attendees.gatherings.gatheringsDatagrid.refresh();
                }, // partial gatherings may have generated even when errors
              });
            } else {
              DevExpress.ui.notify(
                {
                  message: "Can't generate, Please select one single meet with duration, and Filter 'till' earlier than filter 'from'",
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
    } else {
      Attendees.gatherings.filtersForm.getEditor('duration').option('disabled', true);
    }
  },

  toggleEditing: (enabled) => {
    if (Attendees.gatherings.gatheringsDatagrid) {
      Attendees.gatherings.gatheringsDatagrid.option('editing.allowUpdating', enabled);
      Attendees.gatherings.gatheringsDatagrid.option('editing.allowAdding', enabled);
      Attendees.gatherings.gatheringsDatagrid.option('editing.allowDeleting', enabled);
      Attendees.gatherings.gatheringsDatagrid.option('editing.popup.onContentReady', e => e.component.option('toolbarItems[0].visible', enabled));
    }
    if (enabled) {
      Attendees.gatherings.generateGatheringsButton.option('disabled', !Attendees.gatherings.readyToGenerate());
    } else {
      Attendees.gatherings.generateGatheringsButton.option('disabled', !enabled);
    }
  },

  readyToGenerate: () => {
    const filterFrom = Attendees.gatherings.filtersForm.getEditor('filter-from').option('value');
    const filterTill = Attendees.gatherings.filtersForm.getEditor('filter-till').option('value');

    return Attendees.gatherings.selectedMeetHasRule &&
      Attendees.gatherings.filtersForm &&
      Attendees.gatherings.filtersForm.validate().isValid &&
      filterFrom && filterTill && filterTill > filterFrom &&
      Attendees.gatherings.filtersForm.getEditor('meets').option('value') &&
      Attendees.gatherings.filtersForm.getEditor('meets').option('value').length === 1 &&
      Attendees.gatherings.filtersForm.getEditor('duration').option('value') &&
      Attendees.gatherings.filtersForm.getEditor('duration').option('value') > 0
  },

  initFiltersForm: () => {
    $.ajaxSetup({
      headers: {
        'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
      }
    });
    Attendees.gatherings.filtersForm = $('form.filters-dxform').dxForm(Attendees.gatherings.filterFormConfigs).dxForm('instance');
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
        helpText: 'required to generate gatherings',
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
          value: Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['gatheringsListViewOpts'], 'filterFromString') === undefined ? new Date(new Date().setHours(new Date().getHours() - 1)) : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['gatheringsListViewOpts'], 'filterFromString') ? Date.parse(Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['gatheringsListViewOpts'], 'filterFromString')) : null,
          type: 'datetime',
          onValueChanged: (e) => {
            const filterFromString = e.value ? e.value.toJSON() : null;  // it can be null to get all rows
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['gatheringsListViewOpts'], 'filterFromString', filterFromString);
            Attendees.gatherings.generateGatheringsButton && Attendees.gatherings.generateGatheringsButton.option('disabled', !Attendees.gatherings.readyToGenerate());
            if (Attendees.gatherings.filterMeetCheckbox.option('value')) {
              Attendees.gatherings.filtersForm.getEditor('meets').getDataSource().reload();
            }
            const meets = $('div.selected-meets select').val();
            if (meets.length) {
              Attendees.gatherings.gatheringsDatagrid.refresh();
            }
          },
        },
      },
      {
        colSpan: 3,
        cssClass: 'filter-till',
        dataField: 'filter-till',
        helpText: 'required to generate gatherings',
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
          value: Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['gatheringsListViewOpts'], 'filterTillString') === undefined ? new Date(new Date().setMonth(new Date().getMonth() + 1)) : Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['gatheringsListViewOpts'], 'filterTillString') ? Date.parse(Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['gatheringsListViewOpts'], 'filterTillString')) : null,
          type: 'datetime',
          onValueChanged: (e) => {
            const filterTillString = e.value ? e.value.toJSON() : null;  // it can be null to get all rows
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['gatheringsListViewOpts'], 'filterTillString', filterTillString);
            Attendees.gatherings.generateGatheringsButton && Attendees.gatherings.generateGatheringsButton.option('disabled', !Attendees.gatherings.readyToGenerate());
            if (Attendees.gatherings.filterMeetCheckbox.option('value')) {
              Attendees.gatherings.filtersForm.getEditor('meets').getDataSource().reload();
            }  // allow users to screen only active meets by meet's start&finish
            const meets = $('div.selected-meets select').val();
            if (meets.length) {
              Attendees.gatherings.gatheringsDatagrid.refresh();
            }
          },
        },
      },
      {
        dataField: 'meets',
        colSpan: 5,
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
                  Attendees.gatherings.selectAllMeets();
                },
              },
            }
          ],
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
          onValueChanged: (e)=> {
            Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['gatheringsListViewOpts'], 'selectedMeetSlugs', e.value);
            Attendees.gatherings.filtersForm.validate();
            const defaultHelpText = 'Select single one to view/generate gatherings, or multiple one to view';
            Attendees.gatherings.selectedMeetHasRule = 0;
            Attendees.gatherings.generateGatheringsButton && Attendees.gatherings.generateGatheringsButton.option('disabled', true);
            Attendees.gatherings.filtersForm.itemOption('meets', { helpText: defaultHelpText});
            if (e.value && e.value.length > 0) {
              Attendees.gatherings.gatheringsDatagrid.refresh();
              if (e.value.length < 2) {
                const newHelpTexts = [];
                let finalHelpText = '';
                let lastDuration = 0;
                const noRuleText = 'This meet does not have schedules in EventRelation';
                const ruleData = Attendees.gatherings.meetScheduleRules[ e.value[0] ];
                const timeRules = ruleData.rules;
                const meetStart = new Date(ruleData.meetStart).toDateString();
                const meetFinish = new Date(ruleData.meetFinish).toDateString();
                if (timeRules && timeRules.length > 0) {
                  timeRules.forEach(timeRule => {
                    if (timeRule.rule) {
                      Attendees.gatherings.selectedMeetHasRule = timeRules.length;
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
                  if (Attendees.gatherings.generateGatheringsButton && Attendees.gatherings.selectedMeetHasRule && $('div#custom-control-edit-switch').dxSwitch('instance').option('value') && lastDuration > 0) {
                    Attendees.gatherings.generateGatheringsButton.option('disabled', false);
                  }
                } else {
                  finalHelpText = noRuleText;
                }
                Attendees.gatherings.filtersForm.itemOption('duration', {editorOptions: {value: lastDuration, visible: Attendees.gatherings.selectedMeetHasRule < 2}, helpText: Attendees.gatherings.selectedMeetHasRule > 1 ? "Disabled for multiple events" : "minutes"});
                Attendees.gatherings.filtersForm.itemOption('meets', {helpText: finalHelpText});
              }
            }
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {model: 'gathering'};

                if (Attendees.gatherings.filterMeetCheckbox.option('value')) {
                  const filterFrom = $('div.filter-from input')[1].value;
                  const filterTill = $('div.filter-till input')[1].value;
                  params['start'] = filterFrom ? new Date(filterFrom).toISOString() : null;
                  params['finish'] = filterTill ? new Date(filterTill).toISOString() : null;
                  params['grouping'] = 'assembly_name';  // for grouped: true,
                }
                $.get($('form.filters-dxform').data('meets-endpoint-by-slug'), params)
                  .done((result) => {
                    d.resolve(result.data);
                    if (Object.keys(Attendees.gatherings.meetScheduleRules).length < 1 && result.data && result.data[0]) {
                      result.data.forEach( assembly => {
                        assembly.items.forEach( meet => {
                          Attendees.gatherings.meetScheduleRules[meet.slug] = {meetStart: meet.start, meetFinish: meet.finish, rules: meet.schedule_rules, id: meet.id};
                          Attendees.gatherings.meetScheduleRules[meet.id] = {rules: meet.schedule_rules, slug: meet.slug};
                        })
                      }); // schedule rules needed for gatherings generation
                    }
                    const selectedMeetSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['gatheringsListViewOpts'], 'selectedMeetSlugs') || [];
                    Attendees.utilities.selectAllGroupedTags(Attendees.gatherings.filtersForm.getEditor('meets'), selectedMeetSlugs);
                  });
                return d.promise();
              },
            }),
            key: 'slug',
          }),
        },
      },
      {
        colSpan: 1,
        dataField: 'duration',
        editorType: 'dxTextBox',
        helpText: '(minutes)',
        label: {
          location: 'top',
          text: 'duration',
        },
        editorOptions: {
          value: 90,
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
          Attendees.gatherings.gatheringsDatagrid = Attendees.gatherings.initFilteredGatheringsDatagrid(data, itemElement);
        },
      },
    ],
  },

  selectAllMeets: () => {
    const availableMeetsDxTagBox = Attendees.gatherings.filtersForm.getEditor('meets');
    const availableMeetSlugs = availableMeetsDxTagBox.option('items').flatMap(assembly => assembly.items.map(meet => meet.slug));
    availableMeetsDxTagBox.option('value', availableMeetSlugs);
  },  // loop in loop because of options grouped by assembly

  initFilteredGatheringsDatagrid: (data, itemElement) => {
    const $gatheringDatagrid = $("<div id='gatherings-datagrid-container'>").dxDataGrid(Attendees.gatherings.gatheringDatagridConfig);
    itemElement.append($gatheringDatagrid);
    return $gatheringDatagrid.dxDataGrid('instance');
  },

  gatheringDatagridConfig: {
    dataSource: {
      store: new DevExpress.data.CustomStore({
        key: 'id',
        load: (loadOptions) => {
          const meets = $('div.selected-meets select').val();
          const deferred = $.Deferred();
          if (meets && meets.length > 0) {
            const args = {
              requireTotalCount: true,
              take: Attendees.gatherings.gatheringsDatagrid.state().pageSize,
              skip: Attendees.gatherings.gatheringsDatagrid.state().pageSize * Attendees.gatherings.gatheringsDatagrid.state().pageIndex,
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
                  summary: result.summary,
                  groupCount: result.groupCount,
                });
              },
              error: () => {
                deferred.reject("Data Loading Error, probably time out?");
              },
              timeout: 30000,
            });
          } else {
            deferred.resolve([], {totalCount: 0, groupCount: 0});
          }
          return deferred.promise();
        },
        byKey: (key) => {
          const d = new $.Deferred();
          $.get($('form.filters-dxform').data('gatherings-endpoint') + key + '/')
            .done((result) => {
              d.resolve(result.data);
            });
          return d.promise();
        },
        update: (key, values) => {
          return $.ajax({
            url: $('form.filters-dxform').data('gatherings-endpoint') + key + '/',
            method: 'PATCH',
            dataType: 'json',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(values),
            success: (result) => {
              DevExpress.ui.notify(
                {
                  message: 'update gathering success',
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
            url: $('form.filters-dxform').data('gatherings-endpoint'),
            method: 'POST',
            dataType: 'json',
            contentType: 'application/json; charset=utf-8',
            data: JSON.stringify(values),  // ...subject}),
            success: (result) => {
              DevExpress.ui.notify(
                {
                  message: 'Create gathering success',
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
            url: $('form.filters-dxform').data('gatherings-endpoint') + key ,
            method: 'DELETE',
            success: (result) => {
              DevExpress.ui.notify(
                {
                  message: 'removed gathering success',
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
      placeholder: 'search name or locations ...',
    },
    allowColumnReordering: true,
    columnAutoWidth: true,
    allowColumnResizing: true,
    columnResizingMode: 'nextColumn',
    // cellHintEnabled: true,
    hoverStateEnabled: true,
    rowAlternationEnabled: true,
    remoteOperations: {
      groupPaging: true,
    },
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
      storageKey: Attendees.utilities.datagridStorageKeys['gatheringsListView'],
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
        title: 'gatheringEditingArgs',
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
            helpText: 'Address search only works with family name',
          },
          {
            dataField: 'infos.note',
            helpText: 'special memo',
            editorOptions: {
              autoResizeEnabled: true,
            },
          },
          {
            dataField: 'infos.generate_attendance',
            helpText: 'Need auto generation of attendance?',
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
      Attendees.gatherings.gatheringsDatagrid.option('editing.popup.title', 'Adding Gathering');
      const selectedMeetSlugs = Attendees.gatherings.filtersForm.getEditor('meets').option('value');
      if (selectedMeetSlugs && selectedMeetSlugs.length ===1) {
        const selectedMeetSlug = selectedMeetSlugs[0];
        rowData.data.meet = Attendees.gatherings.meetScheduleRules[selectedMeetSlug].id;
      }
    },
    onEditingStart: (e) => {
      const grid = e.component;
      grid.beginUpdate();

      if (e.data && typeof e.data === 'object') {
        Attendees.gatherings.contentTypeEndpoint = Attendees.gatherings.contentTypeEndpoints[e.data['site_type']];
        const prefix = Attendees.utilities.editingEnabled ? 'Editing: ' : 'Info: ';
        grid.option('editing.popup.title', prefix + e.data['gathering_label'] + '@' + e.data['site']);
      }
      grid.option("columns").forEach((column) => {
        grid.columnOption(column.dataField, "allowEditing", Attendees.utilities.editingEnabled);
      });
      grid.endUpdate();
    },
    onEditorPrepared: (e) => {
      if (e.dataField === 'site_id') {
        Attendees.gatherings.siteIdElement = e;
      }
    },
    onToolbarPreparing: (e) => {
      const toolbarItems = e.toolbarOptions.items;
      toolbarItems.unshift({
        location: 'after',
        widget: 'dxButton',
        options: {
          hint: 'Clear Sort/Group/Columns/Meets/Character/Time settings',
          icon: 'clearsquare',
          onClick() {
            if(confirm('Are you sure to clear all settings (Sort/Group/Columns/Meets/Character/Time) in this page?')) {
              Attendees.gatherings.gatheringsDatagrid.state(null);
              window.sessionStorage.removeItem(Attendees.utilities.datagridStorageKeys['gatheringsListViewOpts']);
              Attendees.utilities.selectAllGroupedTags(Attendees.gatherings.filtersForm.getEditor('meets'), []);
              Attendees.gatherings.filtersForm.getEditor('filter-from').option('value', new Date(new Date().setHours(new Date().getHours() - 1)));
              Attendees.gatherings.filtersForm.getEditor('filter-till').option('value', new Date(new Date().setMonth(new Date().getMonth() + 1)));
            }
          },
        }, //
      });
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
              load: (searchOpts) => {
                const d = new $.Deferred();
                const params = {model: 'gathering'};
                if (searchOpts["searchValue"]) {
                  params["searchValue"] = searchOpts["searchValue"];
                  params["searchExpr"] = searchOpts['searchExpr'];
                  params["searchOperation"] = searchOpts['searchOperation'];
                }
                $.get($('form.filters-dxform').data('meets-endpoint-by-id'), params)
                  .done((result) => {
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
        validationRules: [
          {
            type: 'stringLength',
            max: 254,
          }
        ],
        editorOptions: {
          placeholder: 'Example: "The Rock - 12/25/2022"',
        },
        cellTemplate: (cellElement, cellInfo) => {
          cellElement.append ('<u class="text-info">' + cellInfo.data.display_name + '</u>');
        },
      },
      {
        dataField: 'site',
        allowGrouping: false,
        width: '30%',
        readOnly: true,
        caption: 'Location',
      },
      {
        dataField: 'start',
        width: '30%',
        validationRules: [{type: 'required'}],
        dataType: 'datetime',
        format: 'longDateLongTime',
        setCellValue: (newData, value, currentData) => {
          if (value && currentData.meet) {  // setting end time based on the first time role of the chosen meet
            newData.start = value;
            const selectedMeetData = Attendees.gatherings.meetScheduleRules[currentData.meet];
            if (currentData.meet && selectedMeetData) {
              const selectedMeetPrimaryRule = selectedMeetData.rules && selectedMeetData.rules.length > 0 && selectedMeetData.rules[0] || null;
              const selectedMeetLength = selectedMeetPrimaryRule && (new Date(selectedMeetPrimaryRule.end) - new Date(selectedMeetPrimaryRule.start)) || 90*60000;
              newData.finish = new Date(new Date(value).getTime() + selectedMeetLength);
            }
          }
        },
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
      {
        dataField: 'site_type',
        visible: false,
        caption: 'Location type',
        validationRules: [{type: 'required'}],
        editorOptions: {
          placeholder: 'Example: "room"',
        },
        setCellValue: (rowData, value) => {
          rowData.site_id = undefined;
          Attendees.gatherings.contentTypeEndpoint = Attendees.gatherings.contentTypeEndpoints[value];
          rowData.site_type = value;
//          $('div.in-popup-site-id input')[1].value=''; Todo 20210814: can't clear site_id dxlookup after it reload
//          Attendees.gatherings.siteIdElement.value = undefined;
        },
        lookup: {
          hint: 'select a location type',
          valueExpr: 'id',
          displayExpr: (rowData) => rowData.model + ': ' + rowData.hint,
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: (searchOpts) => {
                const d = new $.Deferred();
                $.get($('form.filters-dxform').data('content-type-models-endpoint'), {query: 'location'})
                  .done((result) => {
                    Attendees.gatherings.contentTypeEndpoints = result.data.reduce((obj, item) => ({...obj, [item.id]: item.endpoint}) ,{});
                    d.resolve(result.data);
                  });
                return d.promise();
              },
              byKey: (key) => {
                const d = new $.Deferred();
                $.get($('form.filters-dxform').data('content-type-models-endpoint') + key + '/', {query: 'location'})
                  .done((result) => {
                    if (result.data && result.data[0] && result.data[0].endpoint) {
                      Attendees.gatherings.contentTypeEndpoint = result.data[0].endpoint;
                    }
                    d.resolve(result.data);
                  });
                return d.promise();
              },
            }),
          },
        },
      },
      {
        dataField: 'site_id',
        visible: false,
        cssClass: 'pre-popup-site-id',
        caption: 'Location',
        validationRules: [{type: 'required'}],
        editorOptions: {
          placeholder: 'Example: "Fellowship F201"',
        },
        lookup: {
          allowClearing: true,
          hint: 'select a location',
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: {
            store: new DevExpress.data.CustomStore({
              key: 'id',
              load: (searchArgs) => {
                if (Attendees.gatherings.contentTypeEndpoint) {
                  const d = new $.Deferred();
                  $.get(Attendees.gatherings.contentTypeEndpoint, searchArgs)
                    .done((result) => {
                      d.resolve(result.data);
                    });
                  return d.promise();
                }
              },
              byKey: (key) => {
                if (Attendees.gatherings.contentTypeEndpoint) {
                  const d = new $.Deferred();
                  $.get(Attendees.gatherings.contentTypeEndpoint + key + '/')
                    .done((result) => {
                    if (result && result.id && parseInt(key) === result.id) {
                      result.id = key;
                    }  // Todo: type conversion for integer key of models other than address?
                      d.resolve(result);
                    });
                  return d.promise();
                }
              },
            }),
          },
        },
      },
      {
        dataField: 'infos.generate_attendance',
        visible: false,
        allowGrouping: false,
        caption: 'Auto generate attendance?',
        dataType: 'boolean',
        editorType: 'dxCheckBox',
      },
      {
        dataField: 'infos.note',
        allowGrouping: false,
        editorType: 'dxTextArea',
        caption: 'Note',
        dataType: 'string',
        editorOptions: {
          autoResizeEnabled: true,
        },
      },
    ],
  },
};

$(document).ready(() => {
  Attendees.gatherings.init();
});
