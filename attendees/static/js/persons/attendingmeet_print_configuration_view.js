Attendees.attendingmeetPrintConfiguration = {

  init: () => {
    console.log('static/js/persons/attendingmeet_print_configuration_view.js');
    Attendees.attendingmeetPrintConfiguration.form = $("form#attendingmeet-print-configuration").dxForm(Attendees.attendingmeetPrintConfiguration.formConfig).dxForm('instance');
  },

  submitForm: () => {
    const validationResults = Attendees.attendingmeetPrintConfiguration.form.validate();
    if (validationResults.isValid) {
      if (confirm('Do you want to see the directory for print? (This will take 2 minutes.)')) {
        const formData = Attendees.attendingmeetPrintConfiguration.form.option('formData');
        const searchParams = new URLSearchParams(formData);  // encodeURI break UTF8?
        location.href = `${document.attendingmeetPrintConfigurationForm.action}?${searchParams}`;
      }
    } else {
      alert('Please check the form again. Something missing!');
    }
  },

  formConfig: {
    onContentReady: (e) => {
      e.component.getEditor('divisions').getDataSource().reload();
    },
    items: [
      {
        dataField: "reportTitle",
        editorOptions: {
          value: 'Report Title',
          showClearButton: true,
          buttons: [
            'clear',
          ],
        },
      },
      {
        dataField: "reportDate",
        editorOptions: {
          value: new Date().toLocaleDateString('en', { day: '2-digit', month: 'long', year: 'numeric' }),
          showClearButton: true,
          buttons: [
            'clear',
          ],
        },
      },
      {
        dataField: 'meet',
        isRequired: true,
        validationRules: [{type: 'required'}],
        label: {
          text: 'Select an activity(meet)',
        },
        editorType: 'dxSelectBox',
        editorOptions: {
          valueExpr: 'slug',
          displayExpr: 'display_name',
          searchEnabled: true,
          grouped: true,  // need to send params['grouping'] = 'assembly_name';
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

                $.get(document.attendingmeetPrintConfigurationForm.dataset.meetsEndpointBySlug, params)
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
        dataField: 'divisions',
        editorType: 'dxTagBox',
        validationRules: [{type: 'required'}],
        isRequired: true,
        label: {
          text: 'divisions selector',
        },
        editorOptions: {
          valueExpr: 'slug',
          displayExpr: 'display_name',
          placeholder: 'Select a value...',
          showClearButton: true,
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
                  title: 'select all divisions',
                },
                onClick() {
                  Attendees.utilities.selectAllGroupedTags(Attendees.attendingmeetPrintConfiguration.form.getEditor('divisions'));
                },
              },
            },
          ],
          dataSource: new DevExpress.data.DataSource({
            store: new DevExpress.data.CustomStore({
              key: 'slug',
              loadMode: 'raw',
              load: (e) => {
                const d = $.Deferred();
                $.get(document.attendingmeetPrintConfigurationForm.dataset.divisionsEndpoint).done((response) => {
                  d.resolve(response.data);
                  Attendees.utilities.selectAllGroupedTags(Attendees.attendingmeetPrintConfiguration.form.getEditor('divisions'));
                });
                return d.promise();
              },
            })
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
