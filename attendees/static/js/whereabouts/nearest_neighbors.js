(($, Attendees) => {
  if (typeof Attendees === 'undefined') window.Attendees = {};
  console.log("attendees/static/js/whereabouts/nearest_neighbors.js");

window.Attendees.nearestNeighbors = {
  popup: null,

  initPopupDxForm: (placeId, addressName) => {
    if (!placeId) return;

    const dataSourceUrl = `/whereabouts/api/nearest_neighbors_for/${placeId}/?top=50`;

    if (window.Attendees.nearestNeighbors.popup) {
      // If already initialized, just update the grid data and show
      const grid = $('#nearest-neighbors-grid').dxDataGrid('instance');
      if (grid) {
        grid.option('dataSource', dataSourceUrl);
      }
      window.Attendees.nearestNeighbors.popup.show();
      return;
    }

    window.Attendees.nearestNeighbors.popup = $('div.popup-nearest-neighbors').dxPopup({
      wrapperAttr: {
        'data-testid': 'nearest-neighbors-popup',
      },
      visible: true,
      title: 'Nearest Neighbors for ' + addressName,
      minwidth: '40%',
      minheight: '60%',
      position: {
        my: 'center',
        at: 'center',
        of: window,
      },
      dragEnabled: true,
      showCloseButton: true,
      contentTemplate: (e) => {
        const gridContainer = $('<div id="nearest-neighbors-grid"></div>');
        gridContainer.dxDataGrid({
          dataSource: dataSourceUrl,
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
              caption: 'Address',
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
        e.append(gridContainer);
      }
    }).dxPopup('instance');
  },
};
})(window.jQuery, window.Attendees);
