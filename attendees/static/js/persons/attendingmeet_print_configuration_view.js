Attendees.attendingmeetPrintConfiguration = {

  init: () => {
    console.log('static/js/persons/attendingmeet_print_configuration_view.js');
    Attendees.attendingmeetPrintConfiguration.form = $("form#attendingmeet-print-configuration").dxForm(Attendees.attendingmeetPrintConfiguration.formConfig).dxForm('instance');
  },

  submitForm: () => {
    if (confirm('Do you want to see the directory for print? (This will take 2 minutes.)')){
      alert('Submitted');
    }
  },

  formConfig: {

    formData: {
      reportTitle: "title title title",
      reportDate: new Date(),
    },
    items: [
      {
        dataField: "reportTitle",
      },
      {
        dataField: "reportDate",
      },
      {
        dataField: 'meet',
        // helpText: "Can't show schedules when multiple selected. Select single one to view its schedules",
        // cssClass: 'selected-meets',
        validationRules: [{type: 'required'}],
        label: {
          // location: 'top',
          text: 'Select an activity(meet)',
        },
        editorType: 'dxSelectBox',
        editorOptions: {
          valueExpr: 'slug',
          displayExpr: 'display_name',
          searchEnabled: true,
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
          onValueChanged: (e)=> {
            console.log(" value changed! ");
          },
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              load: (loadOptions) => {
                const d = new $.Deferred();
                const params = {take: 999, grouping: 'assembly_name', model: 'attendingmeet'};  // for grouped: true,

                if (loadOptions.searchValue) {
                  params['searchValue'] = loadOptions.searchValue;
                  params['searchOperation'] = 'contains';
                  params['searchExpr'] = 'display_name';
                }

                $.get(document.attendingmeetPrintConfiguration.dataset.meetsEndpointBySlug, params)
                  .done((result) => {
                    d.resolve(result.data);
                  });
                return d.promise();
              },
            }),
            key: 'slug',
          }),
        },
      },
      {
        itemType: "button",
        horizontalAlignment: 'left',
        buttonOptions: {
          text: "Generate report for print",
          hint: 'Generate attendingmeet report page for printing pdf',
          type: 'default',
          icon: 'print',
          useSubmitBehavior: false,
          onClick: () => Attendees.attendingmeetPrintConfiguration.submitForm(),
        },
      },
    ]
  },
};

$(document).ready(() => {
  Attendees.attendingmeetPrintConfiguration.init();
});
