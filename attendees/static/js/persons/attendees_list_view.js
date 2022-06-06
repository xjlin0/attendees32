Attendees.dataAttendees = {
  meetTagBox: null,
  attendeeDatagrid: null,
  init: () => {
    console.log("attendees/static/js/persons/attendees_list_view.js");
    Attendees.utilities.setAjaxLoaderOnDevExtreme();
    Attendees.dataAttendees.startMeetSelector();
    Attendees.dataAttendees.setDataAttrs();
    Attendees.dataAttendees.setMeetsColumns([]);
    Attendees.dataAttendees.startDataGrid();
  },

  attendeeUrn: null,
  familyAttendancesUrn: null,

  setDataAttrs: () => {
    const $AttendeeAttrs = document.querySelector('div.dataAttendees').dataset;
    Attendees.dataAttendees.familyAttendancesUrn = $AttendeeAttrs.familyAttendancesUrn;
    Attendees.dataAttendees.attendeeUrn = $AttendeeAttrs.attendeeUrn;
  },

  startMeetSelector: () => {
    Attendees.dataAttendees.meetTagBox = $('div.meet-tag-box').dxTagBox({
      dataSource: new DevExpress.data.DataSource({
        store: JSON.parse(document.querySelector('div.dataAttendees').dataset.availableMeets),
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
      onValueChanged: (e) => {
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
        url: "/persons/api/datagrid_data_attendees/",
        dataType: "json",
        data: args,
        success: (result) => {
          deferred.resolve(result.data, {
            totalCount: result.totalCount,
            summary:    result.summary,
            groupCount: result.groupCount
          });
        },
        error: (e) => {
          console.log("loading error, here is error: ", e);
          deferred.reject("Data Loading Error, probably time out?");
        },
        timeout: 99999,
      });

      return deferred.promise();
    }
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
        allowedPageSizes: [10, 30, 5000]
    },
    stateStoring: {
      enabled: true,
      storageKey: "attendeesAttendeesList",
      type: "custom",  // "sessionStorage",
      customLoad: () => JSON.parse(sessionStorage.getItem("attendeesAttendeesList")),
      customSave: (state) => {
        if (state && state.searchText) {state.searchText = "";}  // don't store user search terms
        sessionStorage.setItem("attendeesAttendeesList", JSON.stringify(state));
      },
    },
    columns: null,  // will be initialized later.
    },

  initialAttendeesColumns: [
    {
      caption: "Full name",
      // allowSorting: false,
      dataField: "infos.names",
      name: 'infos.names.original',
      dataType: "string",
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
      dataHtmlTitle: "showing only divisions of current user organization",
      caption: "division",
      dataField: "division",
      lookup: {
        valueExpr: "id",   // valueExpr has to be string, not function
        displayExpr: "display_name",
        dataSource: {
          store: new DevExpress.data.CustomStore({
            key: "id",
            load: () => {
              return $.getJSON($('div.dataAttendees').data('divisions-endpoint'));
            },
          }),
        },
      },
    },
  ],

  otherAttendeesColumns: [
    {
      caption: "Attendance",
      allowSorting: false,
      allowHeaderFiltering: false,
      cellTemplate: (container, rowData) => {
        const attrs = {
          class: 'text-info',
          text: 'Attendances',
          href: Attendees.dataAttendees.familyAttendancesUrn + rowData.data.id,
        };
        $($('<a>', attrs)).appendTo(container);
      },
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
              "class": "text-info",
              "text": Attendees.utilities.phoneNumberFormatter(phoneNumber),
              "href": `tel:${phoneNumber}`,
            };
            if (phones > 0) {$('<span>', {text: ', '}).appendTo(container);}
            $('<a>', attrs).appendTo(container);
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
  ],

  setMeetsColumns: (availableMeets = JSON.parse(document.querySelector('div.dataAttendees').dataset.availableMeets)) => {
    const meetColumns=[];
    // const availableMeets = JSON.parse(document.querySelector('div.dataAttendees').dataset.availableMeets); // $('div.attendings').data('available-meets');

    availableMeets.forEach(meet => {
      meetColumns.push({
        // visible: meet.id > 0,
        caption: meet.display_name,
        dataField: meet.slug,
        allowHeaderFiltering: false,
        calculateCellValue: (rowData) => {
          if (rowData.attendingmeets && rowData.attendingmeets.includes(meet.slug)) {
            return meet.display_name;
          }else{
            return '-';
          }
        }
      })
    });

    Attendees.dataAttendees.dataGridOpts['columns']=[...Attendees.dataAttendees.initialAttendeesColumns, ...meetColumns, ...Attendees.dataAttendees.otherAttendeesColumns]
  },
};

$(document).ready(() => {
  Attendees.dataAttendees.init();
});
