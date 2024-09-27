Attendees.attendingmeetPrintConfiguration = {

  init: () => {
    console.log('static/js/persons/attendingmeet_print_configuration_view.js');
    Attendees.attendingmeetPrintConfiguration.form = $("form#attendingmeet-print-configuration").dxForm(Attendees.attendingmeetPrintConfiguration.formConfig).dxForm('instance');

    window.addEventListener('pageshow', (event) => {
      if (event.persisted || performance.getEntriesByType("navigation")[0].type === 'back_forward') {
        console.log('Re-enabling buttons after back ...');
        document.querySelector('div.spinner-border').classList.add('d-none');
        Attendees.attendingmeetPrintConfiguration.form.getButton('report').option('disabled', false);
        Attendees.attendingmeetPrintConfiguration.form.getButton('envelopes').option('disabled', false);
      }
    });
  },

  submitForm: (confirmMessage, url) => {
    const validationResults = Attendees.attendingmeetPrintConfiguration.form.validate();
    if (validationResults.isValid) {
      if (confirm(confirmMessage)) {
        const formData = Attendees.attendingmeetPrintConfiguration.form.option('formData');
        const searchParams = new URLSearchParams(formData);  // encodeURI break UTF8?
        searchParams.delete("divisions")
        Attendees.attendingmeetPrintConfiguration.form.option('formData').divisions.forEach(d => searchParams.append('divisions', d));
        Attendees.attendingmeetPrintConfiguration.form.getButton('report').option('disabled', true);
        Attendees.attendingmeetPrintConfiguration.form.getButton('envelopes').option('disabled', true);
        document.querySelector('div.spinner-border').classList.remove('d-none');
        location.href = `${url}?${searchParams}`;
      }
    } else {
      alert('Please check the form again. Something missing!');
    }
  },

  formConfig: {
    onContentReady: (e) => {
      e.component.getEditor('divisions').getDataSource().reload();
      e.component.getEditor('meet').getDataSource().reload();
    },
    items: [
      {
        dataField: "reportTitle",
        editorType: 'dxTextArea',
        helpText: '(Optional) Sender address line 1 on envelope, or the Title on reports. Enter for new lines.',
        label: {
          text: 'Text 1',
        },
        editorOptions: {
          height: 100,
          autoResizeEnabled: true,
          value: 'Sample title',
          showClearButton: true,
          buttons: [
            'clear',
          ],
        },
      },
      {
        dataField: "reportDate",
        editorType: 'dxTextArea',
        helpText: '(Optional) Sender address line 2 on envelope, or the date on reports.',
        label: {
          text: 'Text 2',
        },
        editorOptions: {
          height: 70,
          autoResizeEnabled: true,
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
        dataField: 'showPaused',
        helpText: 'show paused participations in reports',
        label: {
          text: 'Show paused participations?',
        },
        dataType: 'boolean',
        editorType: 'dxCheckBox',
      },
      {
        dataField: 'newLines',
        helpText: 'Number of new lines above the recipient label on envelopes only',
        label: {
          text: '# of new lines above recipient on envelope',
        },
        dataType: 'number',
        editorType: 'dxNumberBox',
        editorOptions: {
          value: 2,
          showSpinButtons: true,
          showClearButton: true,
        },
      },
      {
        dataField: 'senderColor',
        helpText: 'Change the color of the sender address on envelopes only',
        label: {
          text: 'Color of the sender on envelopes',
        },
        editorType: 'dxColorBox',
        editorOptions: {
          value: '#0062AE',
        },
      },
      {
        dataField: 'senderInnerWidth',
        helpText: 'The inner width of the sender address controls its position, controls the left margin of the sender address. it should be smaller than outer width. Better to bigger than 16rem',
        label: {
          text: 'Inner width of the sender on envelopes',
        },
        editorOptions: {
          value: '17rem',
        },
      },
      {
        dataField: 'senderOuterWidth',
        helpText: 'The inner width of the sender address controls its position, controls the left margin of the recipient address. it should be bigger than inner width. Better to smaller than 29rem',
        label: {
          text: 'Outer width of the sender on envelopes',
        },
        editorOptions: {
          value: '19rem',
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
        colCount: 12,
        itemType: 'group',
        items: [
          {
            itemType: 'button',
            name: 'report',
            horizontalAlignment: 'left',
            colSpan: 4,
            buttonOptions: {
              text: "Generate report for print",
              hint: 'Generate attendingmeet report page for printing',
              type: 'default',
              icon: 'print',
              useSubmitBehavior: false,
              onClick: () => Attendees.attendingmeetPrintConfiguration.submitForm('Do you want to see the participations for print? (This will take 20 secs. After pages show up, please press Ctrl-P or Cmd-P to print)', document.attendingmeetPrintConfigurationForm.action),
            },
          },
          {
            itemType: 'button',
            name: 'envelopes',
            horizontalAlignment: 'left',
            colSpan: 4,
            buttonOptions: {
              text: "Generate envelopes for print",
              hint: 'Generate attendingmeet envelopes for printing',
              type: 'success',
              icon: 'message',
              useSubmitBehavior: false,
              onClick: () => Attendees.attendingmeetPrintConfiguration.submitForm('Do you want to see the envelopes for print? (This will take 10 secs. After pages show up, please press Ctrl-P or Cmd-P to print) ', document.attendingmeetPrintConfigurationForm.dataset.envelopesUrl),
            },
          },
        ],
      },
    ]
  },
};

$(document).ready(() => {
  Attendees.attendingmeetPrintConfiguration.init();
});
