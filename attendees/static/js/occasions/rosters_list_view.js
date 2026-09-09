const { createApp, ref, reactive, watch, onMounted } = Vue;

const formatDate = (dateString) => {
  if (!dateString) return '';
  const d = new Date(dateString);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
};

const getAttendanceRecord = (rowData, gatheringId) => {
  return rowData.attendances.find(a => String(a.gathering_id) === String(gatheringId));
};

const isCheckedIn = (rowData, gatheringId) => {
  const record = getAttendanceRecord(rowData, gatheringId);
  return record && record.category_id !== 1;
};

const isCheckedOut = (rowData, gatheringId) => {
  const record = getAttendanceRecord(rowData, gatheringId);
  return record && record.finish;
};

const isAttendingValid = (rowData, gathering) => {
  if (!rowData.attendingmeets) return true; // Fallback just in case
  const am = rowData.attendingmeets.find(m => String(m.meet_id) === String(gathering.meet_id));
  if (!am) return false;
  
  const gStart = new Date(gathering.start);
  const amStart = am.start ? new Date(am.start) : new Date('1970-01-01');
  const amFinish = am.finish ? new Date(am.finish) : new Date('2099-12-31');
  
  return gStart >= amStart && gStart <= amFinish;
};

const openAttendeeEdit = (attendeeId) => {
  window.open(`/persons/attendee/${attendeeId}`, '_blank');
};

const app = createApp({
  setup() {
    const filterFormRef = ref(null);
    const dataGridRef = ref(null);

    // Endpoints pulled from DOM dataset
    const appEl = document.getElementById('app');
    const endpoints = {
      rosters: appEl.dataset.rostersEndpoint,
      meets: appEl.dataset.meetsEndpointBySlug,
      attendances: '/occasions/api/organization_meet_character_attendances/'
    };

    const filterData = reactive({
      meets: [],
      startDate: new Date(new Date().setMonth(new Date().getMonth() - 1)), // 1 month ago
      endDate: new Date(new Date().setMonth(new Date().getMonth() + 4)),   // 1 month ahead
      showPhotos: false
    });

    let formInstance = null;
    let gridInstance = null;

    const loadData = () => {
      if (!filterData.meets || !filterData.meets.length) {
        return; 
      }

      if (gridInstance) {
        gridInstance.option('dataSource', new DevExpress.data.CustomStore({
          key: 'attending_id',
          load: async (loadOptions) => {
            try {
              const queryParams = new URLSearchParams();
              filterData.meets.forEach(meet => queryParams.append('meets[]', meet));
              
              if (filterData.startDate) queryParams.set('start', filterData.startDate.toISOString());
              if (filterData.endDate) queryParams.set('finish', filterData.endDate.toISOString());

              queryParams.set('skip', loadOptions.skip || 0);
              queryParams.set('take', loadOptions.take || 40);

              if (loadOptions.sort) {
                queryParams.set('sort', JSON.stringify(loadOptions.sort));
              }

              const response = await fetch(`${endpoints.rosters}?${queryParams.toString()}`);
              if (!response.ok) throw new Error('Network response was not ok');
              
              const data = await response.json();
              
              if (loadOptions.skip === 0 || loadOptions.skip == null) {
                updateGridColumns(data.columns);
              }

              return {
                data: data.rows,
                totalCount: data.totalCount
              };

            } catch (error) {
              DevExpress.ui.notify(`Error loading rosters: ${error.message}`, 'error', 3000);
              console.error(error);
              throw error; 
            }
          }
        }));
      }
    };

    const updateGridColumns = (serverColumns) => {
      const currentCols = gridInstance.option('columns');
      let colsChanged = false;
      
      // +3 because 1 for Attendee name, 1 for Attendances, 1 for dummy column
      if (!currentCols || currentCols.length !== serverColumns.length + 3) {
        colsChanged = true;
      } else {
        for (let i = 0; i < serverColumns.length; i++) {
          if (currentCols[i + 2].name !== String(serverColumns[i].id)) {
            colsChanged = true;
            break;
          }
        }
      }

      if (colsChanged) {
        const columns = [
          {
            dataField: 'attendee_name',
            caption: 'Attendee',
            fixed: true,
            fixedPosition: 'left',
            width: 200,
            cellTemplate: attendeeCellTemplate,
            allowSorting: true
          },
          {
            dataField: 'total_attendances',
            caption: 'Attendances',
            fixed: true,
            fixedPosition: 'left',
            width: 100,
            alignment: 'center',
            allowSorting: true
          }
        ];

        serverColumns.forEach(gathering => {
          columns.push({
            name: String(gathering.id),
            caption: formatDate(gathering.start),
            alignment: 'center',
            gatheringMeta: gathering, // Pass gathering details to cell template
            cellTemplate: attendanceCellTemplate
          });
        });

        // Add a dummy column at the end to absorb remaining horizontal space
        // so that the gathering columns don't stretch out of proportion.
        columns.push({
          caption: '',
          cssClass: 'dummy-column'
        });

        gridInstance.option('columns', columns);
      }
    };

    const toggleAttendance = async (rowData, gatheringId) => {
      const record = getAttendanceRecord(rowData, gatheringId);
      const isCurrentlyCheckedIn = isCheckedIn(rowData, gatheringId);
      const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
      const apiEndpoint = endpoints.attendances;

      let rowUpdated = false;

      try {
        if (isCurrentlyCheckedIn) {
          // Check-out / Undo (Setting back to category 1)
          const response = await fetch(`${apiEndpoint}${record.attendance_id}/`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ category: 1, start: null, finish: null })
          });

          if (!response.ok) throw new Error('Failed to undo check-in');
          record.category_id = 1;
          record.category_name = 'scheduled';
          record.start = null;
          record.finish = null;
          rowData.total_attendances -= 1;
          rowUpdated = true;

        } else {
          const nowIso = new Date().toISOString();
          if (record) {
            // PATCH existing scheduled record
            const response = await fetch(`${apiEndpoint}${record.attendance_id}/`, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
              },
              body: JSON.stringify({ category: 9, start: nowIso, finish: null })
            });

            if (!response.ok) throw new Error('Failed to check in');
            record.category_id = 9;
            record.category_name = 'attended';
            record.start = nowIso;
            record.finish = null;
            rowData.total_attendances += 1;
            rowUpdated = true;

          } else {
            // POST new walk-in record
            const response = await fetch(apiEndpoint, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
              },
              body: JSON.stringify({
                gathering: gatheringId,
                attending: rowData.attending_id,
                character: 1, 
                category: 9,
                start: nowIso
              })
            });

            if (!response.ok) throw new Error('Failed to create walk-in attendance');
            const newAtt = await response.json();
            
            rowData.attendances.push({
              attendance_id: newAtt.id,
              gathering_id: gatheringId,
              category_id: 9,
              category_name: 'attended',
              start: nowIso,
              finish: null
            });
            rowData.total_attendances += 1;
            rowUpdated = true;
          }
        }

        DevExpress.ui.notify('Updated successfully!', 'success', 1500);

      } catch (err) {
        DevExpress.ui.notify(err.message, 'error', 3000);
      }

      if (rowUpdated && gridInstance) {
        const rowIndex = gridInstance.getRowIndexByKey(rowData.attending_id);
        if (rowIndex >= 0) {
          gridInstance.repaintRows([rowIndex]);
        } else {
          gridInstance.repaint(); 
        }
      }
    };

    const markOut = async (rowData, gatheringId) => {
      const record = getAttendanceRecord(rowData, gatheringId);
      if (!record || !record.attendance_id) return;
      
      const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
      const apiEndpoint = endpoints.attendances;
      const isAlreadyOut = !!record.finish;
      const newFinish = isAlreadyOut ? null : new Date().toISOString();

      try {
        const response = await fetch(`${apiEndpoint}${record.attendance_id}/`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({ finish: newFinish })
        });

        if (!response.ok) throw new Error('Failed to checkout');
        
        record.finish = newFinish;
        DevExpress.ui.notify(isAlreadyOut ? 'Checkout undone.' : 'Marked out.', 'success', 1500);

        if (gridInstance) {
          const rowIndex = gridInstance.getRowIndexByKey(rowData.attending_id);
          if (rowIndex >= 0) {
            gridInstance.repaintRows([rowIndex]);
          } else {
            gridInstance.repaint(); 
          }
        }

      } catch (err) {
        DevExpress.ui.notify(err.message, 'error', 3000);
      }
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
      const gatheringMeta = options.column.gatheringMeta;
      const gatheringId = options.column.name;
      
      const wrapper = document.createElement('div');
      wrapper.className = 'text-center';

      // Validation: Is this attending valid for this gathering's time?
      if (!isAttendingValid(data, gatheringMeta)) {
        wrapper.innerHTML = `<span class="not-attending-text">Not Attending</span>`;
        container.append(wrapper);
        return;
      }

      const checkedIn = isCheckedIn(data, gatheringId);
      const checkInBtn = document.createElement('button');
      checkInBtn.className = `roster-btn ${checkedIn ? 'checked-in' : ''}`;
      checkInBtn.innerText = checkedIn ? 'Checked In' : 'Check In';
      checkInBtn.addEventListener('click', () => toggleAttendance(data, gatheringId));
      wrapper.appendChild(checkInBtn);

      if (checkedIn) {
        const checkedOut = isCheckedOut(data, gatheringId);
        const outBtn = document.createElement('button');
        outBtn.className = `roster-btn roster-btn-out ${checkedOut ? 'checked-out' : ''}`;
        outBtn.innerText = checkedOut ? 'Checked Out' : 'Out';
        outBtn.addEventListener('click', () => markOut(data, gatheringId));
        wrapper.appendChild(outBtn);
      }

      container.append(wrapper);
    };

    const initFilterForm = () => {
      formInstance = new DevExpress.ui.dxForm(filterFormRef.value, {
        formData: filterData,
        colCount: 4,
        onFieldDataChanged: (e) => {
          filterData[e.dataField] = e.value;
          if (['meets', 'startDate', 'endDate'].includes(e.dataField)) {
            loadData();
          }
        },
        items: [
          {
            dataField: 'startDate',
            editorType: 'dxDateBox',
            label: { text: 'From' },
            editorOptions: { type: 'datetime', displayFormat: 'shortDateShortTime' }
          },
          {
            dataField: 'endDate',
            editorType: 'dxDateBox',
            label: { text: 'To' },
            editorOptions: { type: 'datetime', displayFormat: 'shortDateShortTime' }
          },
          {
            dataField: 'meets',
            editorType: 'dxTagBox',
            label: { text: 'Meets' },
            editorOptions: {
              grouped: true,
              displayExpr: 'display_name',
              valueExpr: 'slug',
              placeholder: 'Select Meets...',
              dataSource: new DevExpress.data.DataSource({
                store: new DevExpress.data.CustomStore({
                  key: 'slug',
                  load: async () => {
                    const queryParams = new URLSearchParams({
                      take: 9999,
                      grouping: 'assembly_name',
                      model: 'attendance'
                    });
                    
                    if (filterData.startDate) queryParams.set('start', filterData.startDate.toISOString());
                    if (filterData.endDate) queryParams.set('finish', filterData.endDate.toISOString());

                    const response = await fetch(`${endpoints.meets}?${queryParams.toString()}`);
                    if (!response.ok) throw new Error('Failed to load meets');
                    const json = await response.json();
                    return json.data || json;
                  }
                }),
                key: 'slug'
              })
            }
          },
          {
            dataField: 'showPhotos',
            editorType: 'dxCheckBox',
            label: { text: 'Show Photos' }
          }
        ]
      });
    };

    const initDataGrid = () => {
      gridInstance = new DevExpress.ui.dxDataGrid(dataGridRef.value, {
        dataSource: [],
        showBorders: true,
        rowAlternationEnabled: true,
        allowColumnResizing: true,
        columnResizingMode: 'widget',
        columnAutoWidth: true,
        hoverStateEnabled: true,
        noDataText: "No data found. Please select a meet to load.",
        remoteOperations: { paging: true, sorting: true },
        paging: {
          pageSize: 40
        },
        pager: {
          visible: true,
          allowedPageSizes: [40, 200, 9999],
          showPageSizeSelector: true,
          showInfo: true,
          showNavigationButtons: true
        },
        columns: [
          {
            dataField: 'attendee_name',
            caption: 'Attendee',
            fixed: true,
            fixedPosition: 'left',
            width: 200,
            cellTemplate: attendeeCellTemplate
          }
        ]
      });
    };

    watch(() => filterData.showPhotos, () => {
      if (gridInstance) {
        gridInstance.repaint();
      }
    });

    onMounted(() => {
      initFilterForm();
      initDataGrid();
    });

    return {
      filterFormRef,
      dataGridRef,
    };
  }
});

document.addEventListener('DOMContentLoaded', () => {
  app.mount('#app');
});
