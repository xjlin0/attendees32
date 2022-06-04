Attendees.attendances = {
  init: () => {

    console.log("attendees/static/js/occasions/datagrid_assembly_all_attendances.js");
    Attendees.attendances.setDefaults();
    Attendees.attendances.initTempusdominus();
    $('.basic-multiple').select2({
      theme: 'bootstrap4',
    });

    $('form.attendances-filter, div.datetimepickers').on('change, change.datetimepicker', 'select.search-filters, div.datetimepickers', Attendees.utilities.debounce(250, Attendees.attendances.fetchAttendances));
    $('div.for-select-all').on('click', 'input.select-all', e => Attendees.utilities.toggleSelect2All(e, 'select.search-filters'));
    $("div.attendances").dxDataGrid(Attendees.attendances.attendancesFormats);

    Attendees.utilities.setAjaxLoaderOnDevExtreme();
  },

  attendancesFormats: {
    dataSource: null,
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
      enabled: true
    },
    grouping: {
        autoExpandAll: true,
    },
    groupPanel: {
        visible: "auto",
    },
    columnChooser: {
      enabled: true,
      mode: "select",
    },
    columns: [
      {
        dataField: "id",
        allowGrouping: false,
      },
      {
        dataField: "gathering",
        groupIndex: 0,
        lookup: {
            valueExpr: "id",
            displayExpr: "gathering_label",
            dataSource: {
                store: new DevExpress.data.CustomStore({
                    key: "id",
                    load: () => {
                      const $selectedMeets = $('select.filter-meets').val();
                      if ($selectedMeets.length > 0) {
                        return $.getJSON($('div.attendances').data('gatherings-endpoint'), {meets: $selectedMeets});
                      }
                    },
                }),
            },
        }
      },
      {
        caption: 'Attending (Register)',
        dataField: "attending",
        lookup: {
            valueExpr: "id",
            displayExpr: "attending_label",
            dataSource: {
                store: new DevExpress.data.CustomStore({
                    key: "id",
                    load: () => {
                      const $selectedMeets = $('select.filter-meets').val();
                      const $selectedCharacters = $('select.filter-characters').val();
                      if ($selectedMeets.length > 0 && $selectedCharacters.length > 0) {
                        return $.getJSON($('div.attendances').data('attendings-endpoint'), {meets: $selectedMeets, characters: $selectedCharacters});
                        }
                    },
                }),
            },
        }
      },
      {
        dataField: "team",
        lookup: {
            valueExpr: "id",
            displayExpr: "display_name",
            dataSource: {
                store: new DevExpress.data.CustomStore({
                    key: "id",
                    load: () => {
                      const $selectedMeets = $('select.filter-meets').val();
                      if ($selectedMeets.length > 0) {
                        return $.getJSON($('div.attendances').data('teams-endpoint'), {meets: $selectedMeets});
                      }
                    },
                }),
            },
        }
      },
      {
        dataField: "character",
        lookup: {
            valueExpr: "id",
            displayExpr: "display_name",
            dataSource: {
                store: new DevExpress.data.CustomStore({
                    key: "id",
                    load: () => {
                      const $selectedMeets = $('select.filter-meets').val();
                      if ($selectedMeets.length > 0) {
                        return $.getJSON($('div.attendances').data('characters-endpoint'), {meets: $selectedMeets});
                      }
                    },
                }),
            },
        }
      },
      {
        dataField: "category",
        lookup: {
          valueExpr: 'id',
          displayExpr: 'display_name',
          dataSource: (options) => {
            return {
              store: new DevExpress.data.CustomStore({
                key: 'id',
                load: (searchOpts) => {
                  searchOpts.type = 'attendance';
                  return $.getJSON($('div.attendances').data('categories-endpoint'), searchOpts);
                },
                byKey: (key) => {
                  const d = new $.Deferred();
                  $.get($('div.attendances').data('categories-endpoint') + key + '/')
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
        dataField: "modified",
        allowGrouping: false,
        dataType: "datetime"
      },
    ],
  },

  fetchAttendances: (event) => {

    Attendees.utilities.alterCheckBoxAndValidations(event.currentTarget, 'input.select-all');

    let finalUrl = null;
    const $optionForm = $(event.delegateTarget);
    const $meetsSelectBox = $optionForm.find('select.filter-meets');
    const $charactersSelectBox = $optionForm.find('select.filter-characters');
    const meets = $meetsSelectBox.val() || [];
    const characters = $charactersSelectBox.val() || [];
    const startDate = $optionForm.find('input.filter-start-date').val();
    const endDate = $optionForm.find('input.filter-finish-date').val();

    if (startDate && endDate && meets.length && characters.length) {
      const start = (new Date($optionForm.find('input.filter-start-date').val())).toISOString();
      const finish = (new Date($optionForm.find('input.filter-finish-date').val())).toISOString();
      const url = $('div.attendances').data('attendances-endpoint');
      const searchParams = new URLSearchParams({start: start, finish: finish});
      meets.forEach(meet => { searchParams.append('meets[]', meet)});
      characters.forEach(character => { searchParams.append('characters[]', character)});
      finalUrl = `${url}?${searchParams.toString()}`
    }

    $("div.attendances")
      .dxDataGrid("instance")
      .option("dataSource", finalUrl);
  }, // Getting JSON from DRF upon user selecting meet(s)

  fetchAttendancesOld: (event) => {
    const $optionForm=$(event.delegateTarget);
    const $resultElement=$('div.oldAttendances');
    const chosenOptions={
      start: $optionForm.find('input.filter-start-date').val(),
      finish: $optionForm.find('input.filter-finish-date').val(),
      meets: $optionForm.find('select.filter-meets').val(),
    };

    if (chosenOptions.meets) {
    $resultElement.html('<h3> Fetching data .... </h3>');
      $.ajax
      ({
        url      : $optionForm.data('url'),
        data     : chosenOptions,
        success  : (response) => {
                     $resultElement.html(response)
                   },
        error    : (response) => {
                     $resultElement.html('There are some errors: ', response);
                   },
      });
    } else {
      $resultElement.html($resultElement.data('default'));
    }
  }, // Getting html from Django upon user selecting meet(s)

  setDefaults: () => {
    const locale = "en-us"
    const dateOptions = { day: '2-digit', month: '2-digit', year: 'numeric' };
    const timeOptions = { hour12: true, hour: '2-digit', minute:'2-digit' };
    const defaultFilterStartDate = new Date();
    const defaultFilterFinishDate = new Date();
    defaultFilterStartDate.setMonth(defaultFilterStartDate.getMonth() - 3);
    defaultFilterFinishDate.setMonth(defaultFilterFinishDate.getMonth() + 6);
    $('input.filter-start-date').val(defaultFilterStartDate.toLocaleDateString(locale, dateOptions) + ' ' + defaultFilterStartDate.toLocaleTimeString(locale, timeOptions));
    $('input.filter-finish-date').val(defaultFilterFinishDate.toLocaleDateString(locale, dateOptions) + ' ' + defaultFilterFinishDate.toLocaleTimeString(locale, timeOptions));
    document.getElementById('filter-meets').value = [];
  }, // https://stackoverflow.com/a/50000889

  initTempusdominus: () => {
    $.fn.datetimepicker.Constructor.Default = $.extend({},
        $.fn.datetimepicker.Constructor.Default, {
            icons: {
                time: 'fas fa-clock',
                date: 'fas fa-calendar',
                up: 'fas fa-arrow-up',
                down: 'fas fa-arrow-down',
                previous: 'fas fa-arrow-circle-left',
                next: 'fas fa-arrow-circle-right',
                today: 'far fa-calendar-check-o',
                clear: 'fas fa-trash',
                close: 'far fa-times',
            }
        }
    );
  },
}

$(document).ready(() => {
  Attendees.attendances.init();
});
