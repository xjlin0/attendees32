(($, Attendees) => {
  if (typeof Attendees === 'undefined') window.Attendees = {};
  console.log("attendees/static/js/whereabouts/nearest_neighbors.js");

window.Attendees.nearestNeighbors = {
  popup: null,

  createDataSource: (placeId) => {
    return new DevExpress.data.CustomStore({
      key: 'place.id',
      load: (loadOptions) => {
        const deferred = $.Deferred();
        const args = {};
        if (loadOptions.skip) args.skip = loadOptions.skip;
        if (loadOptions.take) args.take = loadOptions.take;
        else args.take = 20;

        if (window.Attendees.nearestNeighbors.meetTagBox) {
          const meets = window.Attendees.nearestNeighbors.meetTagBox.option('value');
          if (meets && meets.length > 0) {
            args['meets[]'] = meets;
          }
        }

        $.ajax({
          url: `/whereabouts/api/nearest_neighbors_for/${placeId}/`,
          dataType: 'json',
          data: args,
          success: (result) => {
            deferred.resolve(result.data, {
              totalCount: result.totalCount
            });
          },
          error: (result) => {
            deferred.reject(result && result.responseJSON && result.responseJSON.detail || 'Nearest Neighbors Data Loading Error');
          },
          timeout: 10000,
        });
        return deferred.promise();
      }
    });
  },

  renderGrid: (dataSource) => {
    const gridContainerElement = document.getElementById('nearest-neighbors-grid');
    if (gridContainerElement) {
      const existingGrid = DevExpress.ui.dxDataGrid.getInstance(gridContainerElement);
      if (existingGrid) {
        existingGrid.dispose();
      }
    }

    $('#nearest-neighbors-grid').dxDataGrid({
      dataSource: dataSource,
      height: '100%',
      remoteOperations: { paging: true },
      scrolling: {
        mode: 'infinite',
        showScrollbar: 'always',
      },
      paging: {
        pageSize: 20,
      },
      showBorders: true,
      columnAutoWidth: true,
      allowColumnResizing: true,
      columnResizingMode: 'nextColumn',
      wordWrapEnabled: false,
      rowAlternationEnabled: true,
      columns: [
        {
          dataField: 'distance',
          caption: 'Direct distance',
          dataType: 'string',
        },
        {
          dataField: 'place.attendee_name',
          caption: 'Attendee',
          cellTemplate: (container, options) => {
            const attendeeId = options.data.place.attendee_id;
            const attendeeName = options.value;
            if (attendeeId) {
              container.append($(`<a target="_blank" href="/persons/attendee/${attendeeId}">${attendeeName}</a>`));
            } else {
              container.append($('<span>').text(attendeeName));
            }
          }
        },
        {
          dataField: 'place.address.display_name',
          caption: 'Address link to map',
          cellTemplate: (container, options) => {
            const addressRaw = options.data.place.address.raw;
            const displayName = options.value;
            if (addressRaw) {
              container.append($(`<a target="_blank" href="https://www.google.com/maps/place/${addressRaw.replaceAll(" ", "+")}">${displayName}</a>`));
            } else {
              container.append($('<span>').text(displayName));
            }
          }
        }
      ],
    });
  },

  initPopupDxForm: (placeId, addressName, availableMeets) => {
    if (!placeId) return;

    const dataSource = window.Attendees.nearestNeighbors.createDataSource(placeId);

    if (window.Attendees.nearestNeighbors.popup) {
      // If already initialized, dispose and recreate grid for new place
      if (window.Attendees.nearestNeighbors.meetTagBox) {
        window.Attendees.nearestNeighbors.meetTagBox.option('value', null);
      }
      window.Attendees.nearestNeighbors.renderGrid(dataSource);
      window.Attendees.nearestNeighbors.popup.option('title', 'Nearest Neighbors for ' + addressName);
      window.Attendees.nearestNeighbors.popup.show();
      return;
    }

    let popupDiv = $('div.popup-nearest-neighbors');
    if (popupDiv.length === 0) {
      popupDiv = $('<div class="popup-nearest-neighbors"></div>').appendTo('body');
    }

    window.Attendees.nearestNeighbors.popup = popupDiv.dxPopup({
      wrapperAttr: {
        'data-testid': 'nearest-neighbors-popup',
        class: 'nearest-neighbors-popup-wrapper',
      },
      visible: true,
      title: 'Nearest Neighbors for ' + addressName,
      width: $(window).width() < 768 ? '100vw' : '60vw',
      height: '80vh',
      position: {
        my: 'center',
        at: 'center',
        of: window,
      },
      dragEnabled: true,
      showCloseButton: true,
      onHidden: (e) => {
        const gridContainerElement = document.getElementById('nearest-neighbors-grid');
        if (gridContainerElement) {
          const grid = DevExpress.ui.dxDataGrid.getInstance(gridContainerElement);
          if (grid) {
            grid.dispose();
          }
        }
        $('#nearest-neighbors-grid').empty();
      },
      contentTemplate: (e) => {
        e.css({ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' });
        const tagBoxContainer = $('<div id="nearest-neighbors-meets" style="margin-bottom: 10px; flex: 0 0 auto;"></div>');
        const gridContainer = $('<div id="nearest-neighbors-grid" style="flex: 1 1 auto; min-height: 0; width: 100%;"></div>');
        e.append(tagBoxContainer);
        e.append(gridContainer);

        if (availableMeets && availableMeets.length > 0) {
          window.Attendees.nearestNeighbors.meetTagBox = tagBoxContainer.dxTagBox({
            label: 'Show attendees joining at least one of activities',
            dataSource: new DevExpress.data.DataSource({
              store: availableMeets,
              key: 'slug',
              group: 'assembly_name'
            }),
            valueExpr: 'slug',
            displayExpr: 'display_name',
            showClearButton: true,
            placeholder: 'Select none for all activities.',
            searchEnabled: true,
            grouped: true,
            onValueChanged: () => {
              const grid = DevExpress.ui.dxDataGrid.getInstance(document.getElementById('nearest-neighbors-grid'));
              if (grid) {
                grid.refresh();
              }
            }
          }).dxTagBox('instance');
        }

        window.Attendees.nearestNeighbors.renderGrid(dataSource);
      }
    }).dxPopup('instance');
  },
};
})(window.jQuery, window.Attendees);
