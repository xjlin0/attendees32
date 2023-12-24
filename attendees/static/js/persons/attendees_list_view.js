Attendees.dataAttendees = {
  meetTagBox: null,
  attendeeDatagrid: null,
  attendeeUrn: null,
  familyAttendancesUrn: null,
  attendeesEndpoint: null,
  attendingmeetsEndpoint: null,
  directoryPreviewPopup: null,
  init: () => {
    console.log("attendees/static/js/persons/attendees_list_view.js");
    const selectedMeetSlugs = Attendees.utilities.accessItemFromSessionStorage(Attendees.utilities.datagridStorageKeys['attendeeListViewOpts'], 'selectedMeetIds') || [];
    const availableMeets = JSON.parse(document.getElementById('organization-available-meets').textContent);
    Attendees.utilities.setAjaxLoaderOnDevExtreme();
    Attendees.dataAttendees.startMeetSelector();
    Attendees.dataAttendees.setDataAttrs();
    Attendees.dataAttendees.setMeetsColumns(availableMeets.filter(meet => selectedMeetSlugs.includes(meet.id)));
    Attendees.dataAttendees.startDataGrid();
    Attendees.dataAttendees.initDirectoryPreview();
  },

  reloadCheckboxesAndPreviewLinks: () => {
    $('div.dataAttendees')
      .off('click', 'u.directory-preview')  // in case of datagrid data change
      .on('click','u.directory-preview', Attendees.dataAttendees.loadDirectoryPreview);

    $('div.dataAttendees')
      .off('change', 'input[type="checkbox"]')  // in case of datagrid data change
      .on('change','input[type="checkbox"]', Attendees.dataAttendees.toggleAttendingMeet);
  },

  setDataAttrs: () => {
    const $AttendeeAttrs = document.querySelector('div.dataAttendees').dataset;
    Attendees.dataAttendees.familyAttendancesUrn = $AttendeeAttrs.familyAttendancesUrn;
    Attendees.dataAttendees.attendeeUrn = $AttendeeAttrs.attendeeUrn;
    Attendees.dataAttendees.attendeesEndpoint = $AttendeeAttrs.attendeesEndpoint;
    Attendees.dataAttendees.attendingmeetsEndpoint = $AttendeeAttrs.attendingmeetsEndpoint;
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

  toggleAttendingMeet: (e) => {
    const checkBox = e.currentTarget;
    checkBox.disabled = true;  // prevent double-clicking
    const deferred = $.Deferred();
    const attendeeId = $(e.currentTarget).parent('td').siblings('td.full-name').first().children('a.text-info').attr('href').split("/").pop();
    console.log("hi 64 here is meetSlug: ", checkBox.value);
    console.log("hi 65 here is attendeeId: ", attendeeId);
    console.log("hi 66 here is action: ", checkBox.checked ? 'join' : 'leave')
    $.ajax({
      url: Attendees.dataAttendees.attendingmeetsEndpoint,
      dataType: 'json',
      method: 'PUT',
      data: {
        meet: e.currentTarget.value,
        action: e.currentTarget.checked ? 'join' : 'leave',
      },
      headers: {
        'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value,
        'X-Target-Attendee-Id': attendeeId,
      },
      timeout: 10000,
      success: (result) => {
        console.log('ajax success! here is result: ', result);
        deferred.resolve();
      },
      error: (e) => {
        console.log('loading directory preview error, here is error: ', e);
        checkBox.checked = !checkBox.checked;
        deferred.reject('Data Loading Error, probably time out?');
      },
      complete: () => {
        checkBox.disabled = false;
      },
    });
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
    remoteOperations: true,
    paging: {
        pageSize:10
    },
    pager: {
        visible: true,
        showPageSizeSelector: true,
        allowedPageSizes: [10, 25, 100, 9999],
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
              text: Attendees.utilities.phoneNumberFormatter(phoneNumber),
              href: `tel:${phoneNumber}`,
            };
            const sms = {
              class: "text-success",
              text: "(SMS)",
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
        cellTemplate: (container, rowData) => {
          if (rowData.data.attendingmeets && rowData.data.attendingmeets.includes(meet.slug)) {
            const preview_url = previews[meet.slug];
            const attr = {
              text: " " + meet.display_name
            };
            if (meet.major_character && meet.audience_editable) {
              $('<input>', {type: 'checkbox', value: meet.slug, checked: 'checked'}).appendTo(container);
            }
            if (preview_url) {
              attr['class'] = 'text-info directory-preview';
              attr['role'] = 'button';
              attr['data-url'] = preview_url + rowData.data.id;
              attr['title'] = `click to see ${rowData.data.infos.names.original} in directory preview.`;
              $('<u>', attr).appendTo(container);
            } else {
              $('<span>', attr).appendTo(container);
            }
          }else{
            if (meet.major_character && meet.audience_editable) {
                $('<input>', {type: 'checkbox', value: meet.slug}).appendTo(container);
            }
            $('<span>', {text: ' -'}).appendTo(container);
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
