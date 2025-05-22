Attendees.dataAttendees = {
  meetTagBox: null,
  attendeeDatagrid: null,
  attendeeUrn: null,
  availableMeets: null,
  meetSlugSet: null,
  familyAttendancesUrn: null,
  attendeesEndpoint: null,
  attendingmeetsDefaultEndpoint: null,
  attendingmeetsUrl: null,
  directoryPreviewPopup: null,
  pausedCategory: null,
  scheduledCategory: null,
  previewAttr: {
    class: 'text-info directory-preview text-decoration-underline',
    role: 'button',
    title: 'click to see the directory preview of ',
  },

  init: () => {
    console.log("attendees/static/js/persons/attendees_list_view.js");
    const selectedMeetSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendeeListViewOpts'], 'selectedMeetIds') || [];
    Attendees.dataAttendees.availableMeets = JSON.parse(document.getElementById('organization-available-meets').textContent);
    Attendees.utilities.setAjaxLoaderOnDevExtreme();
    Attendees.dataAttendees.startMeetSelector();
    Attendees.dataAttendees.setDataAttrs();
    Attendees.dataAttendees.setMeetsColumns(Attendees.dataAttendees.availableMeets.filter(meet => selectedMeetSlugs.includes(meet.id)));
    Attendees.dataAttendees.startDataGrid();
    Attendees.dataAttendees.initDirectoryPreview();
    Attendees.dataAttendees.meetSlugSet = new Set(Attendees.dataAttendees.availableMeets.map(item => item.slug));
  },

  previewAttrs: (previewUrl, attendeeName) => {
    return {
      class: 'text-info directory-preview text-decoration-underline',
      role: 'button',
      title: `click to see ${attendeeName} in directory preview.`,
      'data-url': previewUrl,
    };
  },

  reloadCheckboxesAndPreviewLinks: () => {
    $('div.dataAttendees')
      .off('click', 'span.directory-preview')  // in case of datagrid data change
      .on('click','span.directory-preview', Attendees.dataAttendees.loadDirectoryPreview);

    $('div.dataAttendees')
      .off('change', 'input[type="checkbox"]')  // in case of datagrid data change
      .on('change','input[type="checkbox"]', Attendees.dataAttendees.joinAndLeaveAttendingmeet);

    $('div.dataAttendees')
      .off('dblclick', 'span[id]')  // in case of datagrid data change
      .on('dblclick','span[id]', Attendees.dataAttendees.pauseAndResumeAttendingmeet);
  },

  setDataAttrs: () => {
    const attendeeAttrs = document.querySelector('div.dataAttendees').dataset;
    Attendees.dataAttendees.familyAttendancesUrn = attendeeAttrs.familyAttendancesUrn;
    Attendees.dataAttendees.attendeeUrn = attendeeAttrs.attendeeUrn;
    Attendees.dataAttendees.attendeesEndpoint = attendeeAttrs.attendeesEndpoint;
    Attendees.dataAttendees.attendingmeetsDefaultEndpoint = attendeeAttrs.attendingmeetsDefaultEndpoint;
    Attendees.dataAttendees.attendingmeetsUrl= attendeeAttrs.attendingmeetsUrl;
    Attendees.dataAttendees.scheduledCategory = parseInt(attendeeAttrs.scheduledCategory);
    Attendees.dataAttendees.pausedCategory = parseInt(attendeeAttrs.pausedCategory);
  },

  initDirectoryPreview: () => {
    Attendees.dataAttendees.directoryPreviewPopup = $('div#directory-preview-popup').dxPopup(Attendees.dataAttendees.directoryPreviewPopupConfig).dxPopup('instance');
  },

  directoryPreviewPopupConfig: {
    maxWidth: 900,
    width: '95%',
    height: 350,
    container: '.dataAttendees',
    showTitle: true,
    resizeEnabled: true,
    closeOnOutsideClick: true,
    title: 'Directory Preview',
    dragEnabled: true,
    position: {
      at: 'center',
      my: 'center',
    },
  },

  joinAndLeaveAttendingmeet: (e) => {
    const checkBox = e.currentTarget;
    const action = checkBox.checked ? 'join' : 'leave';
    const $attendeeNodes = $(e.currentTarget).parent('td').siblings('td.full-name').first().children('a.text-info');
    const fullName = $attendeeNodes.first().text();
    const attendeeId = $attendeeNodes.attr('href').split("/").pop();
    if (confirm(`Are you sure to let ${fullName} ${action} the activity?`)) {
      checkBox.disabled = true;
      const deferred = $.Deferred();
      $.ajax({
        url: Attendees.dataAttendees.attendingmeetsDefaultEndpoint,
        dataType: 'json',
        method: 'PUT',
        data: {
          meet: e.currentTarget.value,
          action: action,
        },
        headers: {
          'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
          'X-Target-Attendee-Id': attendeeId,
        },
        timeout: 10000,
        success: (result) => {
          const label = checkBox.nextElementSibling;
          label.style.backgroundColor = null;
          if (action === 'join') {
            label.textContent = ' ' + result.meet__display_name;
            const attrs = Attendees.dataAttendees.previewAttrs(result.preview_url + attendeeId, fullName);
            label.role = attrs.role;
            if (result.preview_url) {
              label.classList = attrs.class;
              label.title = attrs.title;
              label.dataset.url = attrs['data-url'];
            } else {
              if (result.infos__note) {
                label.title = result.infos__note;
              }
              label.dataset.category = result.category;
              label.id = result.id;
            }
          } else {
            label.textContent = ' -';
            label.removeAttribute('class');
            label.removeAttribute('role');
            label.removeAttribute('title');
            label.removeAttribute('id');
          }
          DevExpress.ui.notify(
            {
              message: `${fullName} ${action} ${result.meet__display_name} successfully.`,
              position: {
                my: 'center',
                at: 'center',
                of: window,
              },
            }, 'success', 2000);
          deferred.resolve();
        },
        error: (e) => {
          checkBox.checked = !checkBox.checked;
          DevExpress.ui.notify({
            message: `${fullName} ${action} meet failed: ${e}`,
            position: {
              my: 'center',
              at: 'center',
              of: window,
            },
          }, 'error', 3000);
          deferred.reject('Data Loading Error, probably time out?');
        },
        complete: () => {
          checkBox.disabled = false;
        },
      });
    } else {
      checkBox.checked = !checkBox.checked;
    }
  },

  pauseAndResumeAttendingmeet: (e) => {
    const target = e.currentTarget;
    target.style.backgroundColor = 'Green';
    const $attendeeNodes = $(e.currentTarget).parent('td').siblings('td.full-name').first().children('a.text-info');
    const fullName = $attendeeNodes.first().text();
    const attendeeId = $attendeeNodes.attr('href').split("/").pop();
    const note = e.currentTarget.title ? e.currentTarget.title.split(fullName).pop().trim() : '';
    const message = prompt(`Pause/Resume the activity for ${fullName} ? Add optional note:`, note);
    if (e.currentTarget.dataset.category && message !== null) {  // if user click ok without adding note, it will be empty string ''
      const currentCategory = parseInt(target.dataset.category);
      const nextCategory = currentCategory === Attendees.dataAttendees.pausedCategory ? parseInt(target.dataset.previousCategory) : Attendees.dataAttendees.pausedCategory;
      const nextData = {category: nextCategory};
      if (message) {
        nextData.infos = {note: message};
      }

      fetch(`${Attendees.dataAttendees.attendingmeetsUrl + e.currentTarget.id}/`, {
        method: 'PATCH',
        body: JSON.stringify(nextData),
        headers: {
          'Content-Type': 'application/json',
          'X-Target-Attendee-Id': attendeeId,
          'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
        },
      }).then((response) => {
        return new Promise((resolve) => response.json()
          .then((json) => resolve({
            status: response.status,
            ok: response.ok,
            json,
          })));
      }).then(({ status, json, ok }) => {
        switch (status) {  // https://stackoverflow.com/a/60348315/4257237
          case 200:
            target.dataset.previousCategory = currentCategory;
            target.dataset.category = json.category;
            let notification = `${target.textContent} is resumed for ${fullName}`;
            if (json.category === Attendees.dataAttendees.pausedCategory) {
              target.classList.add('text-decoration-line-through');
              notification = `${target.textContent} is PAUSED for ${fullName} ${json.infos.note || ''}`.trim();
              target.title = notification;
            } else {
              target.classList.remove('text-decoration-line-through');
              if (json.infos.note) {
                target.title = json.infos.note;
              }
            }
            target.style.backgroundColor = null;
            DevExpress.ui.notify(
              {
                message: notification,
                position: {
                  my: 'center',
                  at: 'center',
                  of: window,
                },
              }, 'success', 2000);
            break;
          // case 400:
          //   break;
          // case 500:
          //   break;
          default:
            console.log(`Updating AttendingMeet ${target.id} ${status} error: `, json);
            target.style.backgroundColor = 'Red';
            DevExpress.ui.notify({
              message: `Updating ${fullName} attendingmeet failed with ${status} error: ${json}`,
              position: {
                my: 'center',
                at: 'center',
                of: window,
              },
            }, 'error', 3000);
        }
      })
      .catch(err => {
        console.log(`Updating AttendingMeet ${target.id} error: `, err);
        target.style.backgroundColor = 'Red';
        DevExpress.ui.notify({
          message: `Updating ${fullName} attendingmeet failed with error: ${err}`,
          position: {
            my: 'center',
            at: 'center',
            of: window,
          },
        }, 'error', 3000);
      });
    } else {
      target.style.backgroundColor = null;
    }
  },

  loadDirectoryPreview: (e) => {
    const deferred = $.Deferred();
    const fullName = $(e.currentTarget).parent('td').siblings('td.full-name').first().children('a.text-info').first().text();
    Attendees.dataAttendees.directoryPreviewPopup.option('title', `Directory preview for ${fullName}`);
    Attendees.dataAttendees.directoryPreviewPopup.content().empty();
    let content = 'Sorry the preview cannot be loaded';
    const scrollView = $("<div id='scroll-view'></div>");
    $.ajax({
      url: e.currentTarget.dataset.url,
      dataType: 'html',
      success: (result) => {
        content = result;
        deferred.resolve();
      },
      error: (e) => {
        console.log('loading directory preview error, here is error: ', e);
        deferred.reject('Data Loading Error, probably time out?');
      },
      complete: () => {
        scrollView.append(content);
        scrollView.dxScrollView({
          height: '100%',
          width: '100%'
        });
        Attendees.dataAttendees.directoryPreviewPopup.content().append(scrollView);
        Attendees.dataAttendees.directoryPreviewPopup.show();
      },
      timeout: 10000,
    });
  },

  startMeetSelector: () => {
    const selectedMeetSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendeeListViewOpts'], 'selectedMeetIds') || [];
    Attendees.dataAttendees.meetTagBox = $('div.meet-tag-box').dxTagBox({
      dataSource: new DevExpress.data.DataSource({
        store: JSON.parse(document.getElementById('organization-available-meets').textContent),
        key: 'id',
        group: 'assembly_name'
      }),
      valueExpr: 'id',
      showClearButton: true,
      placeholder: 'select activities...',
      width: '50%',
      searchEnabled: true,
      grouped: true,
      displayExpr: 'display_name',
      value: selectedMeetSlugs,
      onValueChanged: (e) => {
        Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendeeListViewOpts'], 'selectedMeetIds', e.value);
        Attendees.dataAttendees.setMeetsColumns(Attendees.dataAttendees.meetTagBox._selectedItems);
        Attendees.dataAttendees.startDataGrid();
      },
    }).dxTagBox('instance');
  },

  startDataGrid: () => {
    Attendees.dataAttendees.dataGridOpts['dataSource'] = Attendees.dataAttendees.customStore;
    Attendees.dataAttendees.attendeeDatagrid = $("div.dataAttendees").dxDataGrid(Attendees.dataAttendees.dataGridOpts).dxDataGrid("instance");
  },

  customStore: new DevExpress.data.CustomStore({
    key: "id",
    load: (loadOptions) => {
      const deferred = $.Deferred();
      const args = {meets: JSON.stringify(Attendees.dataAttendees.meetTagBox.option('value'))};

      [
        "skip",
        "take",
        "requireTotalCount",
        "requireGroupCount",
        "sort",
        "filter",
        "totalSummary",
        "group",
        "groupSummary"
      ].forEach((i) => {
          if (i in loadOptions && Attendees.utilities.isNotEmpty(loadOptions[i]))
              args[i] = JSON.stringify(loadOptions[i]);
      });

      $.ajax({
        url: Attendees.dataAttendees.attendeesEndpoint,
        dataType: "json",
        data: args,
        success: (result) => {
          deferred.resolve(result.data, {
            totalCount: result.totalCount,
            summary:    result.summary,
            groupCount: result.groupCount
          });
          if (result.totalCount > 0) {
            Attendees.dataAttendees.reloadCheckboxesAndPreviewLinks();
          }
        },
        error: (e) => {
          console.log("loading error, here is error: ", e);
          deferred.reject("Data Loading Error, probably time out?");
        },
        timeout: 99999,
      });

      return deferred.promise();
    },
    byKey: (key) => {
      const d = new $.Deferred();
      $.get(`${Attendees.dataAttendees.attendeesEndpoint}${key}/`)
        .done((result) => {
          d.resolve(result);
        });
      return d.promise();
    },
  }),

  dataGridOpts: {
    dataSource: null, // set later in startDataGrid()
    sorting: {
      mode: "multiple",
    },
    filterRow: { visible: true },  //filter doesn't work with fields with calculateDisplayValue yet
    searchPanel: { visible: true },   //search doesn't work with fields with calculateDisplayValue yet
    allowColumnReordering: true,
    columnAutoWidth: true,
    allowColumnResizing: true,
    columnResizingMode: 'nextColumn',
    rowAlternationEnabled: true,
    hoverStateEnabled: true,
    loadPanel: {
      message: 'Fetching...',
      enabled: true,
    },
    wordWrapEnabled: false,
    grouping: {
      autoExpandAll: true,
    },
//    groupPanel: {
//      visible: "auto",
//    },
    columnChooser: {
      enabled: true,
      mode: "select",
    },
    columnFixing: {
      enabled: true
    },
    onCellPrepared: e => e.rowType === "header" && e.column.dataHtmlTitle && e.cellElement.attr("title", e.column.dataHtmlTitle),

    headerFilter: {
      visible: true
    },
    showBorders: false,
    export: {
      enabled: true,
      allowExportSelectedData: true,  // needs selection mode
      texts: {
        exportAll: 'Export data only on viewed pages',
        exportSelectedRows: 'Export selected rows on viewed pages',
        exportTo: 'Export data on viewed pages',
      },
    },
    onExporting: (e) => {
      const baseUrl = window.location.href.slice(0, -2) + '/';
      const workbook = new ExcelJS.Workbook();
      const worksheet = workbook.addWorksheet('Attendee List');
      worksheet.columns = Array.from({ length: e.component.getVisibleColumns().length }, () => ({ width: 30 }));

      DevExpress.excelExporter.exportDataGrid({
        component: e.component,
        worksheet,
        keepColumnWidths: false,
        topLeftCell: { row: 2, column: 1 },
        customizeCell: (options) => {
          const { gridCell } = options;
          const { excelCell } = options;
          if (gridCell.rowType === 'data') {
            if (['infos.names', 'infos.contacts'].includes(gridCell.column.dataField)) {
              switch(gridCell.column.name) {
                case "infos.contacts.emails":
                  excelCell.value = Attendees.utilities.getValuesByMatchingKeys(gridCell.value, /email/i).join();
                  break;
                case "infos.contacts.phones":
                  excelCell.numFmt = '@';
                  excelCell.value =  Attendees.utilities.getValuesByMatchingKeys(gridCell.value, /phone/i).join();
                  break;
                case "infos.names.original":
                  excelCell.value = { text: gridCell.value.original, hyperlink: baseUrl + gridCell.data.id };
                  excelCell.font = { color: { argb: 'FF0000FF' }, underline: true };
                  break;
                default:
                  excelCell.value = gridCell.value;
              }
              excelCell.alignment = { horizontal: 'left' };
            } else if (Attendees.dataAttendees.meetSlugSet.has(gridCell.column.name)) {
              if (gridCell.value) {
                excelCell.value = Attendees.dataAttendees.pausedCategory === gridCell.value ? 'Paused' : 'Yes';
              } else {
                excelCell.value = 'No';
              }
            }
          }
        },
      }).then(() => {
        workbook.xlsx.writeBuffer().then((buffer) => {
          saveAs(new Blob([buffer], { type: 'application/octet-stream' }), `${document.querySelector('a.navbar-brand').innerText}_${new Date().toLocaleDateString('sv-SE')}.xlsx`);
        });
      });
    }, // https://js.devexpress.com/jQuery/Demos/WidgetsGallery/Demo/DataGrid/ExcelJSCellCustomization
    selection: {
      mode: 'multiple',
      showCheckBoxesMode: 'onLongTap',
    },
    remoteOperations: true,
    paging: {
        pageSize:10
    },
    pager: {
        visible: true,
        showInfo: true,
        showPageSizeSelector: true,
        allowedPageSizes: [10, 25, 100, 9999],
        showNavigationButtons: true,
    },
    stateStoring: {
      enabled: true,
      storageKey: Attendees.utilities.datagridStorageKeys['attendeesAttendeesList'],
      type: "custom",  // "sessionStorage",
      customLoad: () => JSON.parse(sessionStorage.getItem(Attendees.utilities.datagridStorageKeys['attendeesAttendeesList'])),
      customSave: (state) => {
        if (state && state.searchText) {state.searchText = "";}  // don't store user search terms
        sessionStorage.setItem(Attendees.utilities.datagridStorageKeys['attendeesAttendeesList'], JSON.stringify(state));
      },
    },
    columns: null,  // will be initialized later.
    onToolbarPreparing: (e) => {
      const toolbarItems = e.toolbarOptions.items;
      toolbarItems.unshift({
        location: 'after',
        widget: 'dxButton',
        options: {
          hint: 'Reset Sort/Columns/Meets settings',
          icon: 'clearsquare',
          onClick() {
            if(confirm('Are you sure to reset all settings (Sort/Columns/Meets) in this page?')) {
              Attendees.dataAttendees.attendeeDatagrid.state(null);
              window.sessionStorage.removeItem(Attendees.utilities.datagridStorageKeys['attendeeListViewOpts']);
              Attendees.dataAttendees.meetTagBox.option('value', []);
            }
          },
        },
      });
    },
  },

  initialAttendeesColumns: [
    {
      caption: "Full name",
      cssClass: 'full-name',
      dataField: "infos.names",
      name: 'infos.names.original',
      dataType: "string",
      fixed: true,
      fixedPosition: "left",
      allowHeaderFiltering: false,
      cellTemplate: (container, rowData) => {
        const attrs = {
          "class": "text-info",
          "title": "click to see attendee details, click&hold to select multiple",
          "text": rowData.data.infos.names.original,
          "href": Attendees.dataAttendees.attendeeUrn + rowData.data.id,
        };
        $($('<a>', attrs)).appendTo(container);
      },
    },
    {
      dataField: "first_name",
      visible: false,
    },
    {
      dataField: "last_name",
      visible: false,
    },
    {
      dataField: "last_name2",
      visible: false,
    },
    {
      dataField: "first_name2",
      visible: false,
    },
    {
      dataField: "actual_birthday",
      caption: "birthday YMD",
      dataHtmlTitle: "YYYY-MM-DD",
      allowSearch: false,
      visible: false,
    },
    {
      dataField: "estimated_birthday",
      caption: "birthday maybe",
      dataHtmlTitle: "guessed birthday MM-DD",
      calculateCellValue: (rowData) => rowData && rowData.estimated_birthday ? rowData.estimated_birthday.replace('1800-', '????-') : null,
      allowSearch: false,
      visible: false,
    },
    {
      dataHtmlTitle: "click to sort, or click the funnel to select",
      caption: "division & attendance",
      dataField: "division",
      cellTemplate: (container, rowData) => {
        const attrs = {
          class: 'text-body',
          text: rowData.displayValue,
          title: 'click to check all attendances',
          href: Attendees.dataAttendees.familyAttendancesUrn + rowData.data.id,
        };
        $($('<a>', attrs)).appendTo(container);
      },
      lookup: {
        valueExpr: "id",   // valueExpr has to be string, not function
        displayExpr: "display_name",
        dataSource: {
          store: new DevExpress.data.CustomStore({
            key: "id",
            load: () => {
              return $.getJSON($('div.dataAttendees').data('divisions-endpoint'));
            },
            byKey: (key) => {
              const d = new $.Deferred();
              $.get($('div.dataAttendees').data('divisions-endpoint') + key + '/')
                .done((result) => {
                  d.resolve(result);
                });
              return d.promise();
            },
          }),
        },
      },
    },
  ],

  otherAttendeesColumns: [
    {
      dataHtmlTitle: 'click to sort, or type to search. Typing partial date works too',
      dataField: 'visitor_since',
      caption: 'Visit since',
      allowHeaderFiltering: false,
      filterRow: false,
    },
    {
      dataHtmlTitle: 'click to sort, or type to search',
      dataField: 'folkcities',
      caption: 'family cities',
      allowHeaderFiltering: false,  // needs lookup with postprocess to locality id to avoid duplicates
      filterRow: false,
    },
    {
      caption: "Phone",
      dataField: "infos.contacts",
      name: 'infos.contacts.phones',
      allowSorting: false,
      dataType: "string",
      allowHeaderFiltering: false,
      cellTemplate: (container, rowData) => {
        let phones = 0;
        for (let key in rowData.data.infos.contacts) {
          if (key.match(/phone/gi) && rowData.data.infos.contacts[key]) {
            const phoneNumber = rowData.data.infos.contacts[key].trim();
            const attrs = {
              class: "text-info",
              title: "click to call",
              text: Attendees.utilities.phoneNumberFormatter(phoneNumber),
              href: `tel:${phoneNumber}`,
            };
            const sms = {
              class: "text-success",
              text: "(SMS)",
              title: "click to send text messages",
              href: `sms:${phoneNumber}`,
            };
            if (phones > 0) {$('<span>', {text: ', '}).appendTo(container);}
            $('<a>', attrs).appendTo(container);
            $('<a>', sms).appendTo(container);
            phones++;
          }
        }
      },
    },
    {
      caption: 'Email',
      dataField: 'infos.contacts',
      name: 'infos.contacts.emails',
      allowSorting: false,
      dataType: 'string',
      allowHeaderFiltering: false,
      cellTemplate: (container, rowData) => {
        let emails = 0;
        for (let key in rowData.data.infos.contacts) {
          if (key.match(/email/gi) && rowData.data.infos.contacts[key]) {
            const email = rowData.data.infos.contacts[key].trim();
            const attrs = {
              "class": "text-info",
              "text": email,
              "title": "click to send email",
              "href": `mailto:${email}`,
            };
            if (emails > 0) {$('<span>', {text: ', '}).appendTo(container);}
            $('<a>', attrs).appendTo(container);
            emails++;
          }
        }
      },
    },
    {
      dataField: "created",
      visible: false,
      dataType: "datetime",
    },
    {
      dataField: "modified",
      visible: false,
      dataType: "datetime",
    },
  ],

  setMeetsColumns: (availableMeets = JSON.parse(document.getElementById('organization-available-meets').textContent)) => {
    const meetColumns=[];
    const previews = availableMeets.reduce((all, now) => {if (now.infos__preview_url){all[now.slug]=now.infos__preview_url}; return all;}, {});
    availableMeets.forEach(meet => {
      meetColumns.push({
        caption: meet.display_name,
        dataField: meet.slug,
        allowSorting: true,
        headerFilter: {
          dataSource: [
            {
              text: meet.display_name,
              value: ['attendings__meets__slug', '=', meet.slug],
              template: (data) => '<span title="Select all will NOT work">' + data.text + '</span>',
            },
            {
              text: "- Not attending",
              value: ['attendings__meets__slug', '<>', meet.slug],
              template: (data) => '<span title="Select all will NOT work">' + data.text + '</span>',
            },
          ],
        },
        dataType: 'string',
        calculateCellValue: (rowData) => {
          const matchedAttendingmeet = rowData.attendingmeets && rowData.attendingmeets.find(am => am.meet_slug === meet.slug);
          if (matchedAttendingmeet) {
            return matchedAttendingmeet.attendingmeet_category;
          }
          return null;
        },
        cellTemplate: (container, rowData) => {
          const matchedAttendingmeet = rowData.data.attendingmeets && rowData.data.attendingmeets.find(am => am.meet_slug === meet.slug);
          if (matchedAttendingmeet) {
            const previewUrl = previews[meet.slug];
            let attr = {
              text: " " + meet.display_name
            };
            if (meet.major_character && meet.audience_editable) {
              $('<input>', {type: 'checkbox', value: meet.slug, title: 'click to join/leave', checked: 'checked', disabled: rowData.data.deathday !== null}).appendTo(container);
            }
            if (previewUrl) {
              attr = {...Attendees.dataAttendees.previewAttrs(previewUrl + rowData.data.id, rowData.data.infos.names.original), ...attr}
              $('<span>', attr).appendTo(container);
            } else {
              attr['id'] = matchedAttendingmeet.attendingmeet_id;
              attr['data-category'] = matchedAttendingmeet.attendingmeet_category;
              attr['role'] = 'button';
              if (matchedAttendingmeet.attendingmeet_category === Attendees.dataAttendees.pausedCategory) {
                attr['data-previous-category'] = meet.infos__active_category ? meet.infos__active_category : Attendees.dataAttendees.scheduledCategory;
                attr['class'] = 'text-decoration-line-through';
                attr['title'] = `${meet.display_name} is PAUSED for ${rowData.data.infos.names.original} ${matchedAttendingmeet.attendingmeet_note || ''}. Double click to resume`.trim();
              } else {
                if (matchedAttendingmeet.attendingmeet_note) {
                  attr['title'] = matchedAttendingmeet.attendingmeet_note;
                } else {
                  attr['title'] = `Double click text to pause.`;
                }
              }
              $('<span>', attr).appendTo(container);
            }
          }else{
            if (meet.major_character && meet.audience_editable) {
                $('<input>', {type: 'checkbox', title: 'click to join/leave', value: meet.slug, disabled: rowData.data.deathday !== null}).appendTo(container);
            }
            $('<span>', {text: rowData.data.deathday === null ? ' -' : ' ✞✞✞'}).appendTo(container);
          }
        },
      })
    });

    Attendees.dataAttendees.dataGridOpts['columns']=[...Attendees.dataAttendees.initialAttendeesColumns, ...meetColumns, ...Attendees.dataAttendees.otherAttendeesColumns]
  },
};

$(document).ready(() => {
  Attendees.dataAttendees.init();
});
