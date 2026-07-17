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

        $.ajax({
          url: `/whereabouts/api/nearest_neighbors_for/${placeId}/`,
          dataType: 'json',
          data: args,
          success: (result) => {
            deferred.resolve(result.data, {
              totalCount: result.totalCount
            });
          },
          error: () => {
            deferred.reject('Data Loading Error');
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
      },
      paging: {
        pageSize: 20,
      },
      showBorders: true,
      columnAutoWidth: true,
      allowColumnResizing: true,
      rowAlternationEnabled: true,
      columns: [
        {
          dataField: 'distance',
          caption: 'Direct distance',
          dataType: 'string',
          width: '9%',
        },
        {
          dataField: 'place.attendee_name',
          caption: 'Attendee',
          width: '18%',
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

  initPopupDxForm: (placeId, addressName) => {
    if (!placeId) return;

    const dataSource = window.Attendees.nearestNeighbors.createDataSource(placeId);

    if (window.Attendees.nearestNeighbors.popup) {
      // If already initialized, dispose and recreate grid for new place
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
      },
      visible: true,
      title: 'Nearest Neighbors for ' + addressName,
      width: '60vw',
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
        const gridContainer = $('<div id="nearest-neighbors-grid"></div>');
        e.append(gridContainer);
        window.Attendees.nearestNeighbors.renderGrid(dataSource);
      }
    }).dxPopup('instance');
  },
};
})(window.jQuery, window.Attendees);
