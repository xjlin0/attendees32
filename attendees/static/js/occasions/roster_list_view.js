Attendees.roster = {
  filtersForm: null,
  currentCheckbox: null,
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
    Attendees.roster.initCheckOutPopup();
  },

  updateAttendance: (event) => {
    const checkboxInput = event.currentTarget;
    const rowIndex = checkboxInput.getAttribute("name");  // $radioInput.prop('name');
    const buttonValue =  checkboxInput.getAttribute("value"); // $radioInput.prop('value');
    const attendeeName = checkboxInput.parentElement.parentElement.querySelector('u.attendee-name').outerText;

    switch(buttonValue) {
      case "checkIn":
        const checkInCategory = parseInt(checkboxInput.dataset.checkInCategory);
        const scheduledCategory = parseInt(checkboxInput.dataset.scheduledCategory);
        if (checkboxInput.checked) {
          Attendees.roster.attendancesDatagrid.cellValue(rowIndex, 'category', checkInCategory);
          Attendees.roster.attendancesDatagrid.cellValue(rowIndex, 'start', new Date().toISOString());
          Attendees.utilities.callOnce(Attendees.roster.attendancesDatagrid.saveEditData, 500);
        } else {  // maybe user clicking wrong row
          const resultPromise = DevExpress.ui.dialog.confirm(`Remove the time-in record of ${attendeeName} and revert the status back to "scheduled"?`, "UNDO check-in record?");
          resultPromise.done(dialogResult => {
            if (dialogResult) {
              Attendees.roster.attendancesDatagrid.cellValue(rowIndex, 'category', scheduledCategory);
              Attendees.roster.attendancesDatagrid.cellValue(rowIndex, 'start', null);
              Attendees.utilities.callOnce(Attendees.roster.attendancesDatagrid.saveEditData, 500);
            } else {
              checkboxInput.checked = true;
            }
          });
        }
        break;
      case "checkOut":
        if (checkboxInput.checked) {
          Attendees.roster.checkOutPopup.option('title', `Checking out ${attendeeName}`);
          Attendees.roster.currentCheckbox = checkboxInput;
          Attendees.roster.checkOutPopup.show();
          const canvas = document.querySelector("canvas.signature");
          canvas.style.width ='100%';
          canvas.style.height='100%';
          canvas.width  = canvas.offsetWidth;  // https://stackoverflow.com/a/10215724/4257237
          canvas.height = canvas.offsetHeight;

          Attendees.roster.signaturePad = new SignaturePad(canvas, {
            maxWidth: 2,
            backgroundColor: "rgb(255,255,255)",  // for jpg
          });

        } else {  // maybe user clicking wrong row
          const resultPromise = DevExpress.ui.dialog.confirm(`<strong>Clear the time-out record of ${attendeeName} and REMOVE signature?</strong>${checkboxInput.dataset.file ? '<br><img src="' + checkboxInput.dataset.file + '">' : ''}`, "UNDO check-out record?");
          resultPromise.done(dialogResult => {
            if (dialogResult) {
              Attendees.roster.attendancesDatagrid.cellValue(rowIndex, 'finish', null);
              Attendees.roster.attendancesDatagrid.cellValue(rowIndex, 'file', null);  // don't delete files for Audit!!!
              Attendees.utilities.callOnce(Attendees.roster.attendancesDatagrid.saveEditData, 500);
            } else {
              checkboxInput.checked = true;
            }
          });
        }
        break;
      default:  // nothing so far
    }
  },

  reloadRollCallerButtons: () => {
    $('div#attendances-datagrid-container')
      .off('click', 'input.roll-call-button')  // in case of datagrid data change
      .on('click','input.roll-call-button', Attendees.roster.updateAttendance);
  },

  initCheckOutPopup: () => {
    Attendees.roster.checkOutPopup = $('div#signature-canvas-popup').dxPopup(Attendees.roster.checkOutPopupConfig).dxPopup('instance');
  },

  checkOutPopupConfig: {
    visible: false,
    contentTemplate: () => {
      return $('<div width="100%" height="100%">').append(
        $(`<canvas class="signature" width="100%" height="100%"></canvas>`),
      );
    },
    maxWidth: 400,
    width: '95%',
    height: 200,
    container: '.roster-container',
    showTitle: true,
    title: 'Sign here to check out',
    dragEnabled: false,
    hideOnOutsideClick: false,
    showCloseButton: false,
    position: {
      at: 'center',
      my: 'center',
    },
    toolbarItems: [
      {
        widget: 'dxButton',
        toolbar: 'bottom',
        location: 'before',
        options: {
          icon: 'edit',
          text: 'Sign',
          onClick() {
            if (!Attendees.roster.signaturePad.isEmpty()) {
              const currentRowIndex = Attendees.roster.currentCheckbox.getAttribute("name");
              Attendees.roster.checkOutPopup.hide();
              Attendees.roster.attendancesDatagrid.cellValue(currentRowIndex, 'encoded_file', Attendees.roster.signaturePad.toDataURL("image/jpeg", 0.5));
              Attendees.roster.attendancesDatagrid.cellValue(currentRowIndex, 'finish', new Date().toISOString());
              Attendees.utilities.callOnce(Attendees.roster.attendancesDatagrid.saveEditData, 500);
              Attendees.roster.signaturePad.clear();
            } else {
              DevExpress.ui.notify({
                message: 'Checking out requires signature!',
                position: {
                  my: 'center',
                  at: 'center',
                  of: window,
                },
              }, 'error', 3000);
            }
          },
        },
      },
      {
        widget: 'dxButton',
        toolbar: 'bottom',
        location: 'after',
        options: {
          icon: 'clear',
          text: 'Clear signing',
          onClick() {
            Attendees.roster.signaturePad.clear();
          },
        },
      },
      {
        widget: 'dxButton',
        toolbar: 'bottom',
        location: 'after',
        options: {
          text: 'Cancel',
          onClick() {
            Attendees.roster.currentCheckbox.checked = false;
            Attendees.roster.checkOutPopup.hide();
          },
        },
      }
    ],
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
                  take: 999,
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

            if (Attendees.roster.attendancesDatagrid) {
              args['take'] = Attendees.roster.attendancesDatagrid.state().pageSize;
              args['skip'] = Attendees.roster.attendancesDatagrid.state().pageSize * Attendees.roster.attendancesDatagrid.state().pageIndex;
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
                  message: 'update attendance success',
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
                  message: 'Create attendance success',
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
                  message: 'removed attendance success',
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
    sorting: {
      mode: "multiple",
    },
    searchPanel: {
      visible: true,
      width: 150,
      placeholder: 'search name or notes ...',
    },
    filterRow: { visible: true, },
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
      allowedPageSizes: [30, 150, 9999],
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
      visible: true,
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
          icon: 'clearsquare',
          onClick() {
            if(confirm('Are you sure to reset all settings (Sort/Group/Columns/Meets) in this page?')) {
              Attendees.roster.attendancesDatagrid.state(null);
              window.sessionStorage.removeItem(Attendees.utilities.datagridStorageKeys['rollCallListViewOpts']);
              Attendees.roster.filtersForm.getEditor('meets').option('value', null);
            }
          },
        },
      });
      toolbarItems.unshift({
        location: 'after',
        widget: 'dxButton',
        options: {
          hint: 'add existing attendee',
          icon: 'add',
          onClick() {
            if (Attendees.roster.filtersForm.getEditor('gatherings').option('value')) {
              Attendees.roster.attendancesDatagrid.addRow();
            } else {
              alert('Please select a gathering first!');
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
            helpText: 'attendance status',
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
      e.data.gathering = Attendees.roster.filtersForm.getEditor('gatherings').option('value');
      e.data.category = 1;  // scheduled.
      Attendees.roster.attendancesDatagrid.option('editing.popup.title', 'Adding Attendance for ' + Attendees.roster.filtersForm.getEditor('gatherings').option('text'));
    },
    onEditingStart: (e) => {
      const grid = e.component;
      grid.beginUpdate();
      if (e.data && typeof e.data === 'object') {
        grid.option('editing.popup.title', 'Editing Attendance of ' + e.data.attending__attendee__infos__names__original);
      }
      grid.option("columns").forEach((column) => {
        grid.columnOption(column.dataField, "allowEditing", Attendees.utilities.editingEnabled);
      });
      grid.endUpdate();
    },
    onCellPrepared: e => e.rowType === "header" && e.column.dataHtmlTitle && e.cellElement.attr("title", e.column.dataHtmlTitle),
    columns: [
      {
        dataField: 'photo',
        width: 100,
        allowFiltering: false,
        allowSorting: false,
        allowGrouping: false,
        cellTemplate: (container, options) => {
          $(`<a target="_blank" href="/persons/attendee/${options.data.attendee_id}"></a>`)
            .append($('<img>', { class: 'attendee-photo-img', src: options.value }))
            .appendTo(container);
        },
      },
      {
        dataField: 'attending',
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
        sortOrder: 'asc',
        width: 200,
        validationRules: [{type: 'required'}],
        calculateDisplayValue: 'attending__attendee__infos__names__original',  // can't use function when remoteOperations https://supportcenter.devexpress.com/ticket/details/t897726
        cellTemplate: (cellElement, cellInfo) => {  // squeeze to name column for better mobile experience.
          let template = `<a title="Click to open a new page of the attendee info"
                             target="_blank"
                             href="/persons/attendee/${cellInfo.data.attendee_id}">
                            (Info)
                          </a>
                          <u title="click to see the attendance details"
                             class="attendee-name"
                             role="button">
                            ${cellInfo['displayValue']}
                            </u>`;
          if (cellInfo.data.attending__attendee__infos__names__original.includes(' by ')) {  // has registrant
            template += `<a title="Click to open a new page of the registrant info"
                            target="_blank"
                            href="/persons/attendee/${cellInfo.data.registrant_attendee_id}">
                           (Info)
                         </a>`;
          }
          cellElement.append(template);
          if (cellInfo && cellInfo.data) {

            let html = `<br><br>
                          <div class="btn-group-vertical btn-group-sm"
                             role="group">
                          <input type="checkbox"
                                 class="btn-check roll-call-button"
                                 name="${cellInfo.rowIndex}"
                                 value="checkIn"
                                 id="in-${cellInfo.data.id}"
                                 autocomplete="off"
                                 data-check-in-category="9"
                                 data-scheduled-category="1"
                                 ${cellInfo.data.category === 9 ? 'checked' : ''}>
                          <label class="btn btn-outline-success"
                                 for="in-${cellInfo.data.id}">
                            Check in
                          </label>

                          <input type="checkbox"
                                 class="btn-check roll-call-button ${cellInfo.data.start ? '' : 'd-none'}"
                                 name="${cellInfo.rowIndex}"
                                 value="checkOut"
                                 id="out-${cellInfo.data.id}"
                                 autocomplete="off"
                                 data-file="${cellInfo.data.file_path}"
                                 ${cellInfo.data.finish ? 'checked' : ''}>
                          <label class="btn btn-outline-primary ${cellInfo.data.start ? '' : 'd-none'}"
                                 for="out-${cellInfo.data.id}">
                            Check out
                          </label>
                        </div>`;

            if (![1, 9].includes(cellInfo.data.category) && !(cellInfo.data.category in Attendees.roster.buttonCategories)) {  // 1 is scheduled
              html += `<i>(${Attendees.roster.allCategories[cellInfo.data.category]})</i>`
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
                const args = {meets: [meet]};

                if (loadOptions['searchValue']){
                  args['searchValue'] = loadOptions['searchValue'];
                  args['searchExpr'] = loadOptions['searchExpr'];
                  args['searchOperation'] = loadOptions['searchOperation'];
                } else {
                  args['start'] = new Date(filterFrom).toISOString();
                  args['finish'] = new Date(filterTill).toISOString();
                  if (gathering) {
                    args['gatherings'] = [gathering];
                  }
                }  // in search mode user wants what's NOT included in current gatherings

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
                    });  // Todo 20220817 fetch attendingmeet defaults when user searching & adding attendance.
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
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
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
        caption: 'Status',
        visible: false,
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
        dataHtmlTitle: 'hold the "Shift" key and click to apply sorting, hold the "Ctrl" key and click to cancel sorting.',
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
      {
        dataField: 'start',
        caption: 'Time in',
        dataType: 'datetime',
        editorOptions: {
          type: 'datetime',
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        },
      },
      {
        dataField: 'finish',
        caption: 'Time out',
        dataType: 'datetime',
        editorOptions: {
          type: 'datetime',
          dateSerializationFormat: 'yyyy-MM-ddTHH:mm:ss',
        },
      },
      {
        dataField: 'file_path',
        caption: 'signature',
        width: 100,
        allowFiltering: false,
        allowSorting: false,
        allowGrouping: false,
        cellTemplate: (container, options) => {
          if (options.value){
            $('<img>', { src: options.value })
              .appendTo(container);
          }
        },
      },
      {
        dataField: 'infos.note',
        caption: 'Note',
        dataType: 'string',
        editorOptions: {
          autoResizeEnabled: true,
        },
      },
      {
        dataField: 'encoded_file',
        allowFiltering: false,
        allowSorting: false,
        allowGrouping: false,
        dataType: 'string',
        visible: false,
      },
    ],
  },

  resizeCanvas: () => {
      const ratio =  Math.max(window.devicePixelRatio || 1, 1);
      canvas.width = canvas.offsetWidth * ratio;
      canvas.height = canvas.offsetHeight * ratio;
      canvas.getContext("2d").scale(ratio, ratio);
      signaturePad.clear(); // otherwise isEmpty() might return incorrect value
  },  // copied from https://github.com/szimek/signature_pad#tips-and-tricks

};

$(document).ready(() => {
  Attendees.roster.init();
});
