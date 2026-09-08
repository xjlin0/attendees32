const { createApp, ref, reactive, onMounted, watch } = Vue;

let endpoints = {};
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('app');
  endpoints = {
    rosters: container.dataset.rostersEndpoint,
    meets: container.dataset.meetsEndpointBySlug,
  };
});

const app = createApp({
  delimiters: ['[[', ']]'],
  setup() {
    // DOM Refs
    const filterFormRef = ref(null);
    const loadButtonRef = ref(null);
    const dataGridRef = ref(null);

    // State
    const isLoading = ref(false);
    const filterData = reactive({
      meets: [],
      startDate: new Date(new Date().setDate(new Date().getDate() - 30)),
      endDate: new Date(),
      showPhotos: false,
    });
    
    // DevExtreme Component Instances
    let formInstance = null;
    let gridInstance = null;
    let buttonInstance = null;

    const loadData = async () => {
      if (!filterData.meets || !filterData.meets.length) {
        DevExpress.ui.notify('Please select at least one Meet', 'warning', 2000);
        return;
      }

      isLoading.value = true;
      if (buttonInstance) buttonInstance.option('disabled', true);
      
      if (gridInstance) {
        gridInstance.beginCustomLoading("Loading rosters...");
      }

      try {
        const queryParams = new URLSearchParams();
        filterData.meets.forEach(meet => queryParams.append('meets[]', meet));
        
        if (filterData.startDate) queryParams.set('start', filterData.startDate.toISOString());
        if (filterData.endDate) queryParams.set('finish', filterData.endDate.toISOString());

        const response = await fetch(`${endpoints.rosters}?${queryParams.toString()}`);
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();
        
        // Re-configure the grid columns based on the dynamic gatherings
        if (gridInstance) {
          const columns = [
            {
              dataField: 'attendee_name',
              caption: 'Attendee',
              fixed: true,
              cellTemplate: attendeeCellTemplate
            }
          ];

          data.columns.forEach(gathering => {
            columns.push({
              name: String(gathering.id),
              caption: formatDate(gathering.start),
              alignment: 'center',
              cellTemplate: attendanceCellTemplate
            });
          });

          gridInstance.option('columns', columns);
          gridInstance.option('dataSource', data.rows);
        }

      } catch (error) {
        DevExpress.ui.notify(`Error loading rosters: ${error.message}`, 'error', 3000);
        console.error(error);
      } finally {
        isLoading.value = false;
        if (buttonInstance) buttonInstance.option('disabled', false);
        if (gridInstance) gridInstance.endCustomLoading();
      }
    };

    const formatDate = (isoString) => {
      if (!isoString) return '';
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    };

    const getAttendanceRecord = (rowData, gatheringId) => {
      return rowData.attendances[gatheringId];
    };

    const isCheckedIn = (rowData, gatheringId) => {
      const record = getAttendanceRecord(rowData, gatheringId);
      // Category 1 is 'scheduled'. Anything else (like 9 'attended') means they are checked in or handled.
      return record && record.category_id !== 1;
    };

    const toggleAttendance = async (rowData, gatheringId) => {
      const record = getAttendanceRecord(rowData, gatheringId);
      const isCurrentlyCheckedIn = isCheckedIn(rowData, gatheringId);
      const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
      const apiEndpoint = '/occasions/api/organization_meet_character_attendances/';

      if (isCurrentlyCheckedIn) {
        // Revert to 'scheduled' (category 1) and remove start time
        if (!confirm(`Remove the time-in record of ${rowData.attendee_name} and revert status?`)) return;

        try {
          const response = await fetch(`${apiEndpoint}${record.attendance_id}/`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
              category: 1, // scheduled
              start: null
            })
          });

          if (!response.ok) throw new Error('Failed to revert attendance');
          
          record.category_id = 1;
          record.category_name = 'scheduled';
          rowData.total_attendances = Math.max(0, rowData.total_attendances - 1);
          DevExpress.ui.notify('Reverted to scheduled.', 'info', 1500);

        } catch (err) {
          DevExpress.ui.notify(err.message, 'error', 3000);
        }

      } else {
        // Check in: set category 9 (attended) and start time
        try {
          if (record && record.attendance_id) {
            // Update existing scheduled record
            const response = await fetch(`${apiEndpoint}${record.attendance_id}/`, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
              },
              body: JSON.stringify({
                category: 9, // attended
                start: new Date().toISOString()
              })
            });

            if (!response.ok) throw new Error('Failed to check in');
            record.category_id = 9;
            record.category_name = 'attended';
            rowData.total_attendances += 1;

          } else {
            // Walk-in (No scheduled record exists)
            // Create a new attendance record via POST
            const response = await fetch(apiEndpoint, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
              },
              body: JSON.stringify({
                gathering: gatheringId,
                attending: rowData.attending_id,
                character: 1, // Defaulting to 1 for walk-ins (usually student), needs backend enhancement for robust character selection
                category: 9,
                start: new Date().toISOString()
              })
            });

            if (!response.ok) throw new Error('Failed to create walk-in attendance');
            const newAtt = await response.json();
            
            rowData.attendances[gatheringId] = {
              attendance_id: newAtt.id,
              category_id: 9,
              category_name: 'attended'
            };
            rowData.total_attendances += 1;
          }

          DevExpress.ui.notify('Checked in successfully!', 'success', 1500);

        } catch (err) {
          DevExpress.ui.notify(err.message, 'error', 3000);
        }
      }

      if (gridInstance) gridInstance.repaint();
    };

    const markOut = async (rowData, gatheringId) => {
      const record = getAttendanceRecord(rowData, gatheringId);
      if (!record || !record.attendance_id) return;
      
      const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
      const apiEndpoint = '/occasions/api/organization_meet_character_attendances/';

      try {
        const response = await fetch(`${apiEndpoint}${record.attendance_id}/`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            finish: new Date().toISOString()
          })
        });

        if (!response.ok) throw new Error('Failed to checkout');
        DevExpress.ui.notify('Marked out.', 'success', 1500);

      } catch (err) {
        DevExpress.ui.notify(err.message, 'error', 3000);
      }
    };

    const openAttendeeEdit = (attendeeId) => {
      window.open(`/persons/attendee/${attendeeId}`, '_blank');
    };

    // --- DevExtreme Templates ---
    const attendeeCellTemplate = (container, options) => {
      const data = options.data;
      const wrapper = document.createElement('div');
      wrapper.className = 'attendee-info';

      let photoHtml = '';
      if (filterData.showPhotos && data.photo_url) {
        photoHtml = `<img src="${data.photo_url}" class="attendee-photo" alt="Photo">`;
      } else if (filterData.showPhotos) {
        photoHtml = `<div class="attendee-photo d-flex justify-content-center align-items-center bg-light text-muted"><i class="fas fa-user"></i></div>`;
      }

      wrapper.innerHTML = `
        ${photoHtml}
        <span>
          <a href="#" class="attendee-link">${data.attendee_name}</a> 
          <span class="badge badge-info ml-1">(${data.total_attendances})</span>
        </span>
      `;
      
      wrapper.querySelector('.attendee-link').addEventListener('click', (e) => {
        e.preventDefault();
        openAttendeeEdit(data.attendee_id);
      });

      container.append(wrapper);
    };

    const attendanceCellTemplate = (container, options) => {
      const data = options.data;
      const gatheringId = options.column.name;
      const checkedIn = isCheckedIn(data, gatheringId);

      const wrapper = document.createElement('div');
      wrapper.className = 'text-center';

      const checkInBtn = document.createElement('button');
      checkInBtn.className = `roster-btn ${checkedIn ? 'checked-in' : ''}`;
      checkInBtn.innerText = checkedIn ? 'Checked In' : 'Check In';
      checkInBtn.addEventListener('click', () => toggleAttendance(data, gatheringId));
      wrapper.appendChild(checkInBtn);

      if (checkedIn) {
        const outBtn = document.createElement('button');
        outBtn.className = 'roster-btn roster-btn-out';
        outBtn.innerText = 'Out';
        outBtn.addEventListener('click', () => markOut(data, gatheringId));
        wrapper.appendChild(outBtn);
      }

      container.append(wrapper);
    };

    // Re-render grid when showPhotos is toggled
    watch(() => filterData.showPhotos, () => {
      if (gridInstance) {
        gridInstance.repaint();
      }
    });

    onMounted(() => {
      // 1. Initialize Form
      formInstance = new DevExpress.ui.dxForm(filterFormRef.value, {
        formData: filterData,
        colCount: 4,
        onFieldDataChanged: (e) => {
          filterData[e.dataField] = e.value;
        },
        items: [
          {
            dataField: 'meets',
            editorType: 'dxTagBox',
            label: { text: 'Meets' },
            editorOptions: {
              dataSource: new DevExpress.data.CustomStore({
                key: 'slug',
                loadMode: 'raw',
                load: async () => {
                  const response = await fetch(endpoints.meets + '?take=9999');
                  if (!response.ok) throw new Error('Failed to load meets');
                  const json = await response.json();
                  return json.data || json; // Handle DRF paginated vs unpaginated
                }
              }),
              displayExpr: 'display_name',
              valueExpr: 'slug',
              placeholder: 'Select Meets...'
            }
          },
          {
            dataField: 'startDate',
            editorType: 'dxDateBox',
            label: { text: 'From' },
            editorOptions: { type: 'date', displayFormat: 'shortDate' }
          },
          {
            dataField: 'endDate',
            editorType: 'dxDateBox',
            label: { text: 'To' },
            editorOptions: { type: 'date', displayFormat: 'shortDate' }
          },
          {
            dataField: 'showPhotos',
            editorType: 'dxCheckBox',
            label: { text: 'Show Photos' }
          }
        ]
      });

      // 2. Initialize Load Button
      buttonInstance = new DevExpress.ui.dxButton(loadButtonRef.value, {
        text: 'Load Rosters',
        type: 'default',
        stylingMode: 'contained',
        onClick: loadData
      });

      // 3. Initialize DataGrid
      gridInstance = new DevExpress.ui.dxDataGrid(dataGridRef.value, {
        dataSource: [],
        showBorders: true,
        columnAutoWidth: true,
        hoverStateEnabled: true,
        noDataText: "No data found. Please adjust filters and click Load.",
        columns: [
          {
            dataField: 'attendee_name',
            caption: 'Attendee',
            fixed: true,
            cellTemplate: attendeeCellTemplate
          }
        ]
      });
    });

    return {
      filterFormRef,
      loadButtonRef,
      dataGridRef,
    };
  }
});

document.addEventListener('DOMContentLoaded', () => {
  app.mount('#app');
});
